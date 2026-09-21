#!/usr/bin/env python3
"""
Real-time Learning Accelerator
Ultra-fast adaptive learning system that improves AI responses in real-time
Uses micro-learning, instant feedback loops, and predictive adaptation
"""

import asyncio
import time
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
import numpy as np
from datetime import datetime
import threading
import queue
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class LearningEvent:
    """Represents a single learning event"""
    user_id: str
    event_type: str  # 'feedback', 'correction', 'pattern', 'preference'
    original_input: str
    improved_output: str
    confidence_score: float
    context: Dict[str, Any]
    timestamp: float
    learning_priority: int = 1  # 1-10, higher = more important

@dataclass
class MicroPattern:
    """Micro-pattern for instant learning"""
    pattern_id: str
    trigger: str
    replacement: str
    confidence: float
    usage_count: int
    last_success: float
    user_specific: bool = True

@dataclass
class AdaptiveRule:
    """Adaptive rule that evolves with usage"""
    rule_id: str
    condition: str
    action: str
    accuracy: float
    activation_count: int
    evolution_history: List[str] = field(default_factory=list)

class InstantFeedbackProcessor:
    """Processes feedback instantly and creates immediate learning"""
    
    def __init__(self):
        self.feedback_queue = asyncio.Queue(maxsize=1000)
        self.micro_patterns = defaultdict(list)
        self.instant_corrections = defaultdict(dict)
        self.processing_active = True
        
    async def process_instant_feedback(self, user_id: str, original: str, corrected: str, 
                                     feedback_type: str = 'correction', confidence: float = 0.8):
        """Process feedback immediately and create instant learning"""
        
        learning_event = LearningEvent(
            user_id=user_id,
            event_type=feedback_type,
            original_input=original,
            improved_output=corrected,
            confidence_score=confidence,
            context={'feedback_type': feedback_type},
            timestamp=time.time(),
            learning_priority=self._calculate_priority(feedback_type, confidence)
        )
        
        # Add to processing queue
        try:
            await self.feedback_queue.put(learning_event)
        except asyncio.QueueFull:
            logger.warning("Feedback queue full, dropping oldest item")
            try:
                await self.feedback_queue.get()  # Remove oldest
                await self.feedback_queue.put(learning_event)
            except:
                pass
        
        # Instant micro-learning
        await self._instant_micro_learn(learning_event)
    
    def _calculate_priority(self, feedback_type: str, confidence: float) -> int:
        """Calculate learning priority"""
        base_priority = {
            'correction': 9,
            'positive_feedback': 7,
            'negative_feedback': 8,
            'pattern_discovery': 6,
            'preference_update': 5
        }.get(feedback_type, 5)
        
        # Adjust by confidence
        priority = int(base_priority * confidence)
        return max(1, min(10, priority))
    
    async def _instant_micro_learn(self, event: LearningEvent):
        """Create micro-pattern from single feedback event"""
        
        if len(event.original_input) < 3 or len(event.improved_output) < 3:
            return  # Skip very short patterns
        
        # Create micro-pattern
        pattern_id = hashlib.md5(
            f"{event.user_id}_{event.original_input}_{event.improved_output}".encode()
        ).hexdigest()[:16]
        
        micro_pattern = MicroPattern(
            pattern_id=pattern_id,
            trigger=event.original_input.lower().strip(),
            replacement=event.improved_output.strip(),
            confidence=event.confidence_score,
            usage_count=1,
            last_success=time.time(),
            user_specific=True
        )
        
        # Add to user's micro-patterns
        user_patterns = self.micro_patterns[event.user_id]
        
        # Check if similar pattern exists
        existing_pattern = self._find_similar_pattern(user_patterns, micro_pattern)
        
        if existing_pattern:
            # Update existing pattern
            existing_pattern.confidence = (existing_pattern.confidence + micro_pattern.confidence) / 2
            existing_pattern.usage_count += 1
            existing_pattern.last_success = time.time()
        else:
            # Add new pattern
            user_patterns.append(micro_pattern)
            
            # Keep only most recent/useful patterns
            if len(user_patterns) > 100:
                user_patterns.sort(key=lambda p: (p.confidence * p.usage_count, p.last_success))
                self.micro_patterns[event.user_id] = user_patterns[-100:]
        
        # Also store instant correction for immediate use
        self.instant_corrections[event.user_id][event.original_input.lower()] = {
            'replacement': event.improved_output,
            'confidence': event.confidence_score,
            'timestamp': time.time()
        }
        
        logger.debug(f"⚡ Instant micro-learning: {event.original_input} → {event.improved_output}")
    
    def _find_similar_pattern(self, patterns: List[MicroPattern], new_pattern: MicroPattern) -> Optional[MicroPattern]:
        """Find similar existing pattern"""
        
        for pattern in patterns:
            if self._patterns_similar(pattern.trigger, new_pattern.trigger):
                return pattern
        
        return None
    
    def _patterns_similar(self, pattern1: str, pattern2: str, threshold: float = 0.8) -> bool:
        """Check if two patterns are similar"""
        
        if pattern1 == pattern2:
            return True
        
        # Simple similarity check
        words1 = set(pattern1.split())
        words2 = set(pattern2.split())
        
        if not words1 or not words2:
            return False
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        jaccard_similarity = intersection / union if union > 0 else 0
        return jaccard_similarity >= threshold
    
    async def apply_instant_learning(self, user_id: str, text: str) -> Tuple[str, float, List[str]]:
        """Apply instant learning to text"""
        
        corrections_applied = []
        confidence = 1.0
        result_text = text
        
        # Apply instant corrections first (fastest path)
        if user_id in self.instant_corrections:
            text_lower = text.lower()
            
            for trigger, correction_data in self.instant_corrections[user_id].items():
                if trigger in text_lower:
                    # Check if correction is still fresh (within last hour)
                    age_hours = (time.time() - correction_data['timestamp']) / 3600
                    if age_hours < 1.0:
                        result_text = result_text.replace(trigger, correction_data['replacement'])
                        corrections_applied.append(f"instant:{trigger}→{correction_data['replacement']}")
                        confidence = min(confidence, correction_data['confidence'])
        
        # Apply micro-patterns
        if user_id in self.micro_patterns:
            patterns = self.micro_patterns[user_id]
            
            # Sort by confidence and usage
            active_patterns = sorted(
                [p for p in patterns if p.confidence > 0.5],
                key=lambda p: p.confidence * p.usage_count,
                reverse=True
            )
            
            for pattern in active_patterns[:10]:  # Top 10 patterns
                if pattern.trigger in result_text.lower():
                    result_text = result_text.lower().replace(pattern.trigger, pattern.replacement)
                    corrections_applied.append(f"micro:{pattern.trigger}→{pattern.replacement}")
                    confidence = min(confidence, pattern.confidence)
                    
                    # Update pattern usage
                    pattern.usage_count += 1
                    pattern.last_success = time.time()
                    break  # Only apply one micro-pattern per pass
        
        return result_text, confidence, corrections_applied

class PredictiveAdaptationEngine:
    """Predicts user needs and adapts before explicit feedback"""
    
    def __init__(self):
        self.user_behavior_models = defaultdict(dict)
        self.predictive_rules = defaultdict(list)
        self.adaptation_success_rates = defaultdict(float)
        
    def observe_user_behavior(self, user_id: str, behavior_type: str, 
                             context: Dict[str, Any], outcome: str):
        """Observe user behavior for predictive modeling"""
        
        behavior_key = f"{behavior_type}_{context.get('app', 'unknown')}"
        
        if behavior_key not in self.user_behavior_models[user_id]:
            self.user_behavior_models[user_id][behavior_key] = {
                'pattern_frequency': defaultdict(int),
                'outcome_mapping': defaultdict(list),
                'context_patterns': defaultdict(int)
            }
        
        model = self.user_behavior_models[user_id][behavior_key]
        
        # Record pattern frequency
        pattern_signature = self._create_behavior_signature(context)
        model['pattern_frequency'][pattern_signature] += 1
        
        # Record outcome mapping
        model['outcome_mapping'][pattern_signature].append(outcome)
        
        # Record context patterns
        for key, value in context.items():
            if isinstance(value, (str, int)):
                model['context_patterns'][f"{key}:{value}"] += 1
    
    def _create_behavior_signature(self, context: Dict[str, Any]) -> str:
        """Create signature from behavior context"""
        
        signature_parts = []
        
        # Time-based signature
        now = datetime.now()
        signature_parts.append(f"hour:{now.hour}")
        signature_parts.append(f"weekday:{now.weekday()}")
        
        # Context-based signature
        for key in ['app', 'page', 'action', 'input_type']:
            if key in context:
                signature_parts.append(f"{key}:{context[key]}")
        
        return "_".join(signature_parts[:6])  # Limit complexity
    
    async def predict_user_needs(self, user_id: str, current_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Predict what user will need based on current context"""
        
        predictions = []
        
        if user_id not in self.user_behavior_models:
            return predictions
        
        current_signature = self._create_behavior_signature(current_context)
        user_models = self.user_behavior_models[user_id]
        
        # Analyze each behavior model
        for behavior_key, model in user_models.items():
            
            # Find similar past contexts
            similar_patterns = []
            for pattern, frequency in model['pattern_frequency'].items():
                similarity = self._calculate_pattern_similarity(current_signature, pattern)
                if similarity > 0.6 and frequency > 2:
                    similar_patterns.append((pattern, frequency, similarity))
            
            # Sort by similarity and frequency
            similar_patterns.sort(key=lambda x: x[1] * x[2], reverse=True)
            
            # Create predictions from top patterns
            for pattern, frequency, similarity in similar_patterns[:3]:
                if pattern in model['outcome_mapping']:
                    outcomes = model['outcome_mapping'][pattern]
                    
                    # Find most common outcome
                    outcome_counts = defaultdict(int)
                    for outcome in outcomes:
                        outcome_counts[outcome] += 1
                    
                    if outcome_counts:
                        most_common = max(outcome_counts.items(), key=lambda x: x[1])
                        prediction_confidence = (most_common[1] / len(outcomes)) * similarity
                        
                        if prediction_confidence > 0.4:
                            predictions.append({
                                'behavior_type': behavior_key,
                                'predicted_outcome': most_common[0],
                                'confidence': prediction_confidence,
                                'basis': f"Similar pattern occurred {frequency} times"
                            })
        
        return sorted(predictions, key=lambda x: x['confidence'], reverse=True)[:5]
    
    def _calculate_pattern_similarity(self, pattern1: str, pattern2: str) -> float:
        """Calculate similarity between behavior patterns"""
        
        parts1 = set(pattern1.split('_'))
        parts2 = set(pattern2.split('_'))
        
        if not parts1 or not parts2:
            return 0.0
        
        intersection = len(parts1 & parts2)
        union = len(parts1 | parts2)
        
        return intersection / union if union > 0 else 0.0
    
    async def create_adaptive_rule(self, user_id: str, prediction: Dict[str, Any]) -> Optional[AdaptiveRule]:
        """Create adaptive rule from prediction"""
        
        if prediction['confidence'] < 0.6:
            return None
        
        rule_id = hashlib.md5(
            f"{user_id}_{prediction['behavior_type']}_{prediction['predicted_outcome']}".encode()
        ).hexdigest()[:16]
        
        # Create condition based on behavior type
        condition = f"behavior_type == '{prediction['behavior_type']}'"
        
        # Create action based on predicted outcome
        action = f"prepare_for_outcome('{prediction['predicted_outcome']}')"
        
        rule = AdaptiveRule(
            rule_id=rule_id,
            condition=condition,
            action=action,
            accuracy=prediction['confidence'],
            activation_count=0
        )
        
        self.predictive_rules[user_id].append(rule)
        
        # Keep only most accurate rules
        if len(self.predictive_rules[user_id]) > 20:
            self.predictive_rules[user_id].sort(key=lambda r: r.accuracy, reverse=True)
            self.predictive_rules[user_id] = self.predictive_rules[user_id][:20]
        
        return rule

class ContinuousLearningEngine:
    """Continuously learns and adapts without explicit training phases"""
    
    def __init__(self):
        self.learning_streams = defaultdict(deque)
        self.adaptation_models = {}
        self.learning_velocity = defaultdict(float)  # How fast user learns
        self.concept_drift_detectors = defaultdict(list)
        
    async def stream_learning_event(self, user_id: str, event_data: Dict[str, Any]):
        """Add learning event to continuous stream"""
        
        timestamp = time.time()
        event_data['timestamp'] = timestamp
        
        # Add to learning stream
        self.learning_streams[user_id].append(event_data)
        
        # Keep stream size manageable
        if len(self.learning_streams[user_id]) > 500:
            self.learning_streams[user_id].popleft()
        
        # Trigger continuous learning
        await self._continuous_adapt(user_id, event_data)
    
    async def _continuous_adapt(self, user_id: str, new_event: Dict[str, Any]):
        """Continuously adapt model with new event"""
        
        # Calculate learning velocity
        self._update_learning_velocity(user_id)
        
        # Detect concept drift
        if await self._detect_concept_drift(user_id, new_event):
            logger.info(f"🔄 Concept drift detected for {user_id}, adapting model")
            await self._handle_concept_drift(user_id)
        
        # Update adaptation model
        await self._update_adaptation_model(user_id, new_event)
    
    def _update_learning_velocity(self, user_id: str):
        """Calculate how quickly user is learning/changing"""
        
        user_stream = self.learning_streams[user_id]
        
        if len(user_stream) < 10:
            return
        
        # Look at recent events to calculate change rate
        recent_events = list(user_stream)[-10:]
        
        # Calculate variety in recent events
        event_types = set(event.get('event_type', 'unknown') for event in recent_events)
        contexts = set(str(event.get('context', {})) for event in recent_events)
        
        # Learning velocity based on variety and frequency
        time_span = recent_events[-1]['timestamp'] - recent_events[0]['timestamp']
        if time_span > 0:
            frequency = len(recent_events) / time_span  # events per second
            variety = len(event_types) + len(contexts)
            
            self.learning_velocity[user_id] = frequency * variety
        
    async def _detect_concept_drift(self, user_id: str, new_event: Dict[str, Any]) -> bool:
        """Detect if user's patterns are changing significantly"""
        
        user_stream = self.learning_streams[user_id]
        
        if len(user_stream) < 50:
            return False
        
        # Compare recent patterns to historical patterns
        recent_events = list(user_stream)[-20:]  # Recent
        historical_events = list(user_stream)[-50:-20]  # Historical
        
        # Calculate pattern distributions
        recent_patterns = self._extract_pattern_distribution(recent_events)
        historical_patterns = self._extract_pattern_distribution(historical_events)
        
        # Calculate KL divergence or simple difference
        drift_score = self._calculate_pattern_drift(recent_patterns, historical_patterns)
        
        # Threshold based on learning velocity
        drift_threshold = 0.5 + (self.learning_velocity[user_id] * 0.1)
        
        return drift_score > drift_threshold
    
    def _extract_pattern_distribution(self, events: List[Dict[str, Any]]) -> Dict[str, float]:
        """Extract pattern distribution from events"""
        
        pattern_counts = defaultdict(int)
        total_events = len(events)
        
        for event in events:
            # Create pattern from key event attributes
            pattern_parts = []
            
            if 'event_type' in event:
                pattern_parts.append(f"type:{event['event_type']}")
            
            if 'context' in event and isinstance(event['context'], dict):
                for key, value in list(event['context'].items())[:3]:  # Limit complexity
                    pattern_parts.append(f"{key}:{value}")
            
            pattern = "_".join(pattern_parts)
            pattern_counts[pattern] += 1
        
        # Convert to distribution
        return {pattern: count / total_events for pattern, count in pattern_counts.items()}
    
    def _calculate_pattern_drift(self, recent: Dict[str, float], historical: Dict[str, float]) -> float:
        """Calculate drift between pattern distributions"""
        
        all_patterns = set(recent.keys()) | set(historical.keys())
        
        if not all_patterns:
            return 0.0
        
        total_difference = 0.0
        
        for pattern in all_patterns:
            recent_prob = recent.get(pattern, 0.0)
            historical_prob = historical.get(pattern, 0.0)
            total_difference += abs(recent_prob - historical_prob)
        
        return total_difference / 2  # Normalize
    
    async def _handle_concept_drift(self, user_id: str):
        """Handle detected concept drift"""
        
        # Increase learning rate temporarily
        original_velocity = self.learning_velocity[user_id]
        self.learning_velocity[user_id] = min(original_velocity * 2, 10.0)
        
        # Schedule velocity reduction after adaptation period
        asyncio.create_task(self._reduce_learning_velocity_later(user_id, original_velocity))
        
        # Reset some adaptation models to allow new patterns
        if user_id in self.adaptation_models:
            # Keep only high-confidence adaptations
            old_model = self.adaptation_models[user_id]
            self.adaptation_models[user_id] = {
                k: v for k, v in old_model.items() 
                if isinstance(v, dict) and v.get('confidence', 0) > 0.8
            }
    
    async def _reduce_learning_velocity_later(self, user_id: str, original_velocity: float):
        """Reduce learning velocity back to normal after adaptation period"""
        await asyncio.sleep(300)  # 5 minutes
        self.learning_velocity[user_id] = original_velocity
    
    async def _update_adaptation_model(self, user_id: str, event: Dict[str, Any]):
        """Update continuous adaptation model"""
        
        if user_id not in self.adaptation_models:
            self.adaptation_models[user_id] = {}
        
        model = self.adaptation_models[user_id]
        
        # Extract adaptable features from event
        if event.get('event_type') == 'correction':
            original = event.get('original_input', '')
            corrected = event.get('improved_output', '')
            
            if original and corrected:
                adaptation_key = f"correction_{original.lower()}"
                
                if adaptation_key not in model:
                    model[adaptation_key] = {
                        'replacement': corrected,
                        'confidence': event.get('confidence_score', 0.5),
                        'usage_count': 1,
                        'last_used': time.time()
                    }
                else:
                    # Update existing adaptation
                    existing = model[adaptation_key]
                    existing['confidence'] = (existing['confidence'] + event.get('confidence_score', 0.5)) / 2
                    existing['usage_count'] += 1
                    existing['last_used'] = time.time()
                    
                    # Update replacement if new one has higher confidence
                    if event.get('confidence_score', 0.5) > existing['confidence']:
                        existing['replacement'] = corrected

class RealTimeLearningAccelerator:
    """Main accelerator that coordinates all real-time learning components"""
    
    def __init__(self):
        self.feedback_processor = InstantFeedbackProcessor()
        self.predictive_engine = PredictiveAdaptationEngine()
        self.continuous_engine = ContinuousLearningEngine()
        self.acceleration_active = True
        
        # Performance metrics
        self.learning_stats = defaultdict(lambda: {
            'events_processed': 0,
            'adaptations_created': 0,
            'predictions_made': 0,
            'accuracy_score': 0.0
        })
    
    async def accelerate_learning(self, user_id: str, event_type: str, 
                                 original_input: str, improved_output: str, 
                                 context: Dict[str, Any] = None, confidence: float = 0.8):
        """Main entry point for accelerated learning"""
        
        if not self.acceleration_active:
            return
        
        # Process instant feedback
        await self.feedback_processor.process_instant_feedback(
            user_id, original_input, improved_output, event_type, confidence
        )
        
        # Stream to continuous learning
        await self.continuous_engine.stream_learning_event(user_id, {
            'event_type': event_type,
            'original_input': original_input,
            'improved_output': improved_output,
            'context': context or {},
            'confidence_score': confidence
        })
        
        # Observe behavior for prediction
        if context:
            self.predictive_engine.observe_user_behavior(
                user_id, event_type, context, improved_output
            )
        
        # Update stats
        self.learning_stats[user_id]['events_processed'] += 1
        
        logger.debug(f"⚡ Accelerated learning: {user_id} - {event_type}")
    
    async def apply_accelerated_learning(self, user_id: str, text: str, 
                                       context: Dict[str, Any] = None) -> Tuple[str, float, List[str]]:
        """Apply all accelerated learning to input text"""
        
        if not self.acceleration_active:
            return text, 1.0, []
        
        # Apply instant learning
        improved_text, confidence, corrections = await self.feedback_processor.apply_instant_learning(
            user_id, text
        )
        
        # Get predictive adaptations
        if context:
            predictions = await self.predictive_engine.predict_user_needs(user_id, context)
            
            # Apply high-confidence predictions
            for prediction in predictions:
                if prediction['confidence'] > 0.8:
                    # Create adaptive rule
                    rule = await self.predictive_engine.create_adaptive_rule(user_id, prediction)
                    if rule:
                        corrections.append(f"predictive:{rule.rule_id}")
        
        return improved_text, confidence, corrections
    
    async def get_learning_insights(self, user_id: str) -> Dict[str, Any]:
        """Get insights about user's learning acceleration"""
        
        stats = self.learning_stats[user_id]
        
        # Get micro-patterns count
        micro_patterns_count = len(self.feedback_processor.micro_patterns[user_id])
        
        # Get instant corrections count
        instant_corrections_count = len(self.feedback_processor.instant_corrections[user_id])
        
        # Get learning velocity
        learning_velocity = self.continuous_engine.learning_velocity[user_id]
        
        # Get prediction count
        predictive_rules_count = len(self.predictive_engine.predictive_rules[user_id])
        
        return {
            'events_processed': stats['events_processed'],
            'micro_patterns_learned': micro_patterns_count,
            'instant_corrections_available': instant_corrections_count,
            'predictive_rules_active': predictive_rules_count,
            'learning_velocity': learning_velocity,
            'acceleration_active': self.acceleration_active,
            'learning_efficiency_score': min(1.0, (micro_patterns_count + instant_corrections_count) / 100)
        }
    
    def toggle_acceleration(self, active: bool):
        """Toggle learning acceleration on/off"""
        self.acceleration_active = active
        logger.info(f"🚀 Learning acceleration {'enabled' if active else 'disabled'}")
    
    async def optimize_performance(self):
        """Optimize accelerator performance"""
        
        # Clean up old instant corrections
        current_time = time.time()
        
        for user_id, corrections in self.feedback_processor.instant_corrections.items():
            expired_keys = []
            
            for trigger, correction_data in corrections.items():
                age_hours = (current_time - correction_data['timestamp']) / 3600
                
                if age_hours > 24:  # Remove corrections older than 24 hours
                    expired_keys.append(trigger)
            
            for key in expired_keys:
                del corrections[key]
        
        # Clean up old micro-patterns
        for user_id, patterns in self.feedback_processor.micro_patterns.items():
            # Remove patterns not used in last 7 days
            active_patterns = [
                p for p in patterns 
                if (current_time - p.last_success) < 7 * 24 * 3600
            ]
            
            self.feedback_processor.micro_patterns[user_id] = active_patterns
        
        logger.debug("🧹 Learning accelerator performance optimized")


# Global learning accelerator
learning_accelerator = RealTimeLearningAccelerator()

# Easy integration functions
async def accelerate_user_learning(user_id: str, event_type: str, original: str, 
                                 improved: str, context: Dict[str, Any] = None, 
                                 confidence: float = 0.8):
    """Add learning event to acceleration system"""
    await learning_accelerator.accelerate_learning(
        user_id, event_type, original, improved, context, confidence
    )

async def apply_accelerated_improvements(user_id: str, text: str, 
                                       context: Dict[str, Any] = None) -> Tuple[str, float, List[str]]:
    """Apply accelerated learning improvements to text"""
    return await learning_accelerator.apply_accelerated_learning(user_id, text, context)

async def get_user_learning_insights(user_id: str) -> Dict[str, Any]:
    """Get learning insights for user"""
    return await learning_accelerator.get_learning_insights(user_id)

def toggle_learning_acceleration(active: bool):
    """Toggle learning acceleration system"""
    learning_accelerator.toggle_acceleration(active)

async def initialize_realtime_learning_accelerator():
    """Initialize the real-time learning acceleration system"""
    logger.info("⚡ Real-time Learning Accelerator initialized")
    
    # Start background optimization
    asyncio.create_task(_background_accelerator_optimization())
    
    return True

async def _background_accelerator_optimization():
    """Background optimization for learning accelerator"""
    
    while True:
        try:
            await learning_accelerator.optimize_performance()
            await asyncio.sleep(300)  # Optimize every 5 minutes
        except Exception as e:
            logger.error(f"Learning accelerator optimization error: {e}")
            await asyncio.sleep(300)