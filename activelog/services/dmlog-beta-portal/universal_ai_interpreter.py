#!/usr/bin/env python3
"""
Universal AI Interpreter Layer for SuperInstance
Personal ML-powered translation layer between what users say/type and what AI systems receive
Gets better at translation over time for each individual user
"""

import os
import json
import sqlite3
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.ensemble import RandomForestRegressor, GradientBoostingClassifier
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_squared_error, accuracy_score
from sklearn.model_selection import train_test_split
import pickle
import re
import hashlib
from concurrent.futures import ThreadPoolExecutor
import threading

logger = logging.getLogger(__name__)

@dataclass
class InterpretationContext:
    """Context for an interpretation request"""
    user_id: str
    app_name: str
    task_type: str  # 'voice_command', 'text_input', 'search_query', 'creative_prompt', etc.
    session_id: str
    device_type: str  # 'mobile', 'desktop', 'tablet', 'smart_speaker'
    time_of_day: str
    user_state: str  # 'focused', 'distracted', 'multitasking', 'relaxed'
    previous_interactions: List[str]
    environment_noise: float  # 0.0 to 1.0
    urgency_level: float  # 0.0 to 1.0

@dataclass
class InterpretationResult:
    """Result of an interpretation"""
    original_input: str
    interpreted_input: str
    confidence: float
    interpretation_method: str
    context_factors: Dict[str, Any]
    suggested_improvements: List[str]
    timestamp: datetime

@dataclass
class UserInterpretationProfile:
    """Personal interpretation profile for each user"""
    user_id: str
    speech_patterns: Dict[str, Any]
    vocabulary_preferences: Dict[str, str]  # user_word -> preferred_ai_word
    context_adaptations: Dict[str, Any]
    task_specializations: Dict[str, Any]  # Different patterns for different tasks
    learning_confidence: float
    interpretation_history: List[InterpretationResult] = field(default_factory=list)
    personal_shortcuts: Dict[str, str] = field(default_factory=dict)
    error_patterns: Dict[str, int] = field(default_factory=dict)

class PersonalAIInterpreter:
    """Personal AI interpreter for individual users"""
    
    def __init__(self, user_id: str, profile: UserInterpretationProfile = None):
        self.user_id = user_id
        self.profile = profile or UserInterpretationProfile(user_id=user_id, 
                                                           speech_patterns={},
                                                           vocabulary_preferences={},
                                                           context_adaptations={},
                                                           task_specializations={},
                                                           learning_confidence=0.3)
        
        # Personal ML models
        self.vocabulary_translator = TfidfVectorizer(max_features=500, lowercase=True)
        self.context_adapter = RandomForestRegressor(n_estimators=50)
        self.quality_predictor = MLPRegressor(hidden_layer_sizes=(50, 20), max_iter=500)
        self.pattern_classifier = GradientBoostingClassifier(n_estimators=50)
        
        # Personal learning data
        self.training_data = []
        self.is_trained = False
        self.last_training = None
        
        # Real-time adaptation
        self.recent_interactions = []
        self.adaptation_buffer = []
    
    async def interpret(self, raw_input: str, context: InterpretationContext) -> InterpretationResult:
        """Interpret user input through personal ML lens"""
        
        # Start with the raw input
        interpreted = raw_input
        confidence = 0.5
        methods_used = []
        
        # Apply personal vocabulary translation
        interpreted, vocab_confidence = self.apply_vocabulary_translation(interpreted, context)
        confidence = (confidence + vocab_confidence) / 2
        methods_used.append('vocabulary_translation')
        
        # Apply speech pattern corrections
        interpreted, speech_confidence = self.apply_speech_pattern_correction(interpreted, context)
        confidence = (confidence + speech_confidence) / 2
        methods_used.append('speech_pattern_correction')
        
        # Apply context-based adaptations
        interpreted, context_confidence = self.apply_context_adaptation(interpreted, context)
        confidence = (confidence + context_confidence) / 2
        methods_used.append('context_adaptation')
        
        # Apply task-specific optimizations
        interpreted, task_confidence = self.apply_task_optimization(interpreted, context)
        confidence = (confidence + task_confidence) / 2
        methods_used.append('task_optimization')
        
        # Apply personal shortcuts and macros
        interpreted, shortcut_confidence = self.apply_personal_shortcuts(interpreted, context)
        confidence = (confidence + shortcut_confidence) / 2
        methods_used.append('personal_shortcuts')
        
        # Generate suggested improvements
        suggestions = self.generate_improvement_suggestions(raw_input, interpreted, context)
        
        result = InterpretationResult(
            original_input=raw_input,
            interpreted_input=interpreted,
            confidence=confidence,
            interpretation_method=' + '.join(methods_used),
            context_factors={
                'app_name': context.app_name,
                'task_type': context.task_type,
                'user_state': context.user_state,
                'time_of_day': context.time_of_day,
                'device_type': context.device_type
            },
            suggested_improvements=suggestions,
            timestamp=datetime.now()
        )
        
        # Store for learning
        self.recent_interactions.append(result)
        if len(self.recent_interactions) > 20:
            self.recent_interactions.pop(0)
        
        return result
    
    def apply_vocabulary_translation(self, input_text: str, context: InterpretationContext) -> Tuple[str, float]:
        """Apply personal vocabulary preferences"""
        translated = input_text
        confidence = 0.7  # Base confidence
        
        # Apply learned vocabulary mappings
        words = input_text.lower().split()
        translated_words = []
        
        for word in words:
            if word in self.profile.vocabulary_preferences:
                preferred = self.profile.vocabulary_preferences[word]
                translated_words.append(preferred)
                confidence = min(1.0, confidence + 0.1)  # Boost confidence for known mappings
            else:
                translated_words.append(word)
        
        if translated_words != words:
            translated = ' '.join(translated_words)
        
        # Apply context-specific vocabulary
        context_vocab = self.profile.task_specializations.get(context.task_type, {}).get('vocabulary', {})
        for user_term, ai_term in context_vocab.items():
            if user_term.lower() in translated.lower():
                translated = re.sub(r'\b' + re.escape(user_term) + r'\b', ai_term, 
                                  translated, flags=re.IGNORECASE)
                confidence = min(1.0, confidence + 0.05)
        
        return translated, confidence
    
    def apply_speech_pattern_correction(self, input_text: str, context: InterpretationContext) -> Tuple[str, float]:
        """Correct personal speech patterns and habits"""
        corrected = input_text
        confidence = 0.6
        
        speech_patterns = self.profile.speech_patterns
        
        # Correct common personal mispronunciations/misinterpretations
        if 'common_errors' in speech_patterns:
            for error, correction in speech_patterns['common_errors'].items():
                if error.lower() in corrected.lower():
                    corrected = re.sub(r'\b' + re.escape(error) + r'\b', correction,
                                     corrected, flags=re.IGNORECASE)
                    confidence = min(1.0, confidence + 0.15)
        
        # Handle personal verbal habits
        if 'verbal_habits' in speech_patterns:
            habits = speech_patterns['verbal_habits']
            
            # Remove filler words if user tends to use them
            if habits.get('uses_fillers', False):
                filler_words = ['um', 'uh', 'like', 'you know', 'actually', 'basically']
                for filler in filler_words:
                    corrected = re.sub(r'\b' + filler + r'\b', '', corrected, flags=re.IGNORECASE)
                corrected = re.sub(r'\s+', ' ', corrected).strip()
                confidence = min(1.0, confidence + 0.1)
            
            # Handle incomplete sentences if user tends to trail off
            if habits.get('incomplete_sentences', False) and not corrected.strip().endswith(('.', '!', '?')):
                # Try to complete based on context and patterns
                completion = self.predict_sentence_completion(corrected, context)
                if completion:
                    corrected += completion
                    confidence = min(1.0, confidence + 0.1)
        
        # Handle device-specific errors
        if context.device_type == 'mobile' and 'mobile_errors' in speech_patterns:
            for error, correction in speech_patterns['mobile_errors'].items():
                corrected = corrected.replace(error, correction)
        
        return corrected, confidence
    
    def apply_context_adaptation(self, input_text: str, context: InterpretationContext) -> Tuple[str, float]:
        """Adapt interpretation based on context"""
        adapted = input_text
        confidence = 0.7
        
        context_adaptations = self.profile.context_adaptations
        
        # Time-of-day adaptations
        time_adaptations = context_adaptations.get('time_of_day', {})
        if context.time_of_day in time_adaptations:
            adaptations = time_adaptations[context.time_of_day]
            
            # Apply time-specific interpretations
            for pattern, replacement in adaptations.get('patterns', {}).items():
                if pattern.lower() in adapted.lower():
                    adapted = re.sub(r'\b' + re.escape(pattern) + r'\b', replacement,
                                   adapted, flags=re.IGNORECASE)
                    confidence = min(1.0, confidence + 0.08)
        
        # User state adaptations
        state_adaptations = context_adaptations.get('user_state', {})
        if context.user_state in state_adaptations:
            state_rules = state_adaptations[context.user_state]
            
            # If user is distracted, be more explicit
            if context.user_state == 'distracted' and 'clarify_ambiguous' in state_rules:
                adapted = self.clarify_ambiguous_terms(adapted, context)
                confidence = max(0.5, confidence - 0.1)  # Lower confidence when distracted
            
            # If user is focused, can be more concise
            if context.user_state == 'focused' and 'make_concise' in state_rules:
                adapted = self.make_more_concise(adapted)
                confidence = min(1.0, confidence + 0.1)
        
        # Environment noise adaptations
        if context.environment_noise > 0.5:
            # High noise - likely speech recognition errors
            adapted = self.correct_likely_speech_errors(adapted, context.environment_noise)
            confidence = max(0.4, confidence - (context.environment_noise * 0.3))
        
        return adapted, confidence
    
    def apply_task_optimization(self, input_text: str, context: InterpretationContext) -> Tuple[str, float]:
        """Apply task-specific optimizations"""
        optimized = input_text
        confidence = 0.7
        
        task_specs = self.profile.task_specializations.get(context.task_type, {})
        
        if context.task_type == 'voice_command':
            # Make commands more explicit and actionable
            optimized = self.optimize_for_voice_command(optimized, task_specs)
            confidence = min(1.0, confidence + 0.1)
        
        elif context.task_type == 'creative_prompt':
            # Enhance creative prompts with learned preferences
            optimized = self.optimize_for_creative_prompt(optimized, task_specs)
            confidence = min(1.0, confidence + 0.05)
        
        elif context.task_type == 'search_query':
            # Optimize search queries
            optimized = self.optimize_for_search(optimized, task_specs)
            confidence = min(1.0, confidence + 0.08)
        
        elif context.task_type == 'text_input':
            # General text optimization
            optimized = self.optimize_for_text_input(optimized, task_specs)
        
        return optimized, confidence
    
    def apply_personal_shortcuts(self, input_text: str, context: InterpretationContext) -> Tuple[str, float]:
        """Apply personal shortcuts and macros"""
        expanded = input_text
        confidence = 0.8
        
        # Apply personal shortcuts
        for shortcut, expansion in self.profile.personal_shortcuts.items():
            if shortcut.lower() in expanded.lower():
                expanded = re.sub(r'\b' + re.escape(shortcut) + r'\b', expansion,
                                expanded, flags=re.IGNORECASE)
                confidence = min(1.0, confidence + 0.15)
        
        # Apply app-specific shortcuts
        app_shortcuts = self.profile.task_specializations.get(context.app_name, {}).get('shortcuts', {})
        for shortcut, expansion in app_shortcuts.items():
            if shortcut.lower() in expanded.lower():
                expanded = re.sub(r'\b' + re.escape(shortcut) + r'\b', expansion,
                                expanded, flags=re.IGNORECASE)
                confidence = min(1.0, confidence + 0.1)
        
        return expanded, confidence
    
    def optimize_for_voice_command(self, command: str, task_specs: Dict) -> str:
        """Optimize input specifically for voice commands"""
        optimized = command
        
        # Add action words if missing
        if not self.has_action_word(command):
            learned_actions = task_specs.get('preferred_actions', ['please'])
            if learned_actions:
                optimized = f"{learned_actions[0]} {command}"
        
        # Make more specific based on app context
        if 'specificity_patterns' in task_specs:
            for pattern, replacement in task_specs['specificity_patterns'].items():
                optimized = re.sub(pattern, replacement, optimized, flags=re.IGNORECASE)
        
        return optimized
    
    def optimize_for_creative_prompt(self, prompt: str, task_specs: Dict) -> str:
        """Optimize input for creative AI tasks"""
        optimized = prompt
        
        # Add learned creative modifiers
        modifiers = task_specs.get('preferred_modifiers', [])
        if modifiers and len(prompt.split()) < 10:  # Short prompts can be enhanced
            selected_modifier = modifiers[hash(prompt) % len(modifiers)]
            optimized = f"{prompt} {selected_modifier}"
        
        # Add style preferences
        if 'style_preferences' in task_specs:
            style = task_specs['style_preferences'].get('default')
            if style and 'style' not in prompt.lower():
                optimized += f" in a {style} style"
        
        return optimized
    
    def optimize_for_search(self, query: str, task_specs: Dict) -> str:
        """Optimize search queries"""
        optimized = query
        
        # Add learned search modifiers
        if 'search_modifiers' in task_specs:
            for trigger, modifier in task_specs['search_modifiers'].items():
                if trigger.lower() in query.lower():
                    optimized += f" {modifier}"
                    break
        
        # Fix common search patterns
        if 'pattern_fixes' in task_specs:
            for pattern, fix in task_specs['pattern_fixes'].items():
                optimized = re.sub(pattern, fix, optimized, flags=re.IGNORECASE)
        
        return optimized
    
    def optimize_for_text_input(self, text: str, task_specs: Dict) -> str:
        """General text input optimization"""
        optimized = text
        
        # Apply learned text patterns
        if 'text_patterns' in task_specs:
            for pattern, replacement in task_specs['text_patterns'].items():
                optimized = re.sub(pattern, replacement, optimized, flags=re.IGNORECASE)
        
        return optimized
    
    def has_action_word(self, text: str) -> bool:
        """Check if text contains an action word"""
        action_words = ['set', 'get', 'create', 'delete', 'update', 'find', 'search', 
                       'go', 'move', 'attack', 'cast', 'roll', 'check', 'log', 
                       'schedule', 'remind', 'navigate', 'please', 'can you', 'would you']
        
        text_lower = text.lower()
        return any(action in text_lower for action in action_words)
    
    def predict_sentence_completion(self, partial: str, context: InterpretationContext) -> str:
        """Predict how user would complete a sentence"""
        # Simple completion based on common patterns
        partial_lower = partial.lower().strip()
        
        if partial_lower.endswith(('set', 'create', 'make')):
            return " a new item"
        elif partial_lower.endswith(('find', 'search', 'look for')):
            return " something"
        elif partial_lower.endswith(('go to', 'navigate to')):
            return " the location"
        
        return ""
    
    def clarify_ambiguous_terms(self, text: str, context: InterpretationContext) -> str:
        """Clarify ambiguous terms based on context"""
        clarified = text
        
        # Common ambiguous terms and their likely meanings in context
        ambiguous_terms = {
            'it': self.resolve_pronoun('it', context),
            'that': self.resolve_pronoun('that', context),
            'there': self.resolve_location_reference(context)
        }
        
        for term, clarification in ambiguous_terms.items():
            if clarification and term in clarified.lower():
                clarified = re.sub(r'\b' + term + r'\b', clarification, 
                                 clarified, flags=re.IGNORECASE)
        
        return clarified
    
    def resolve_pronoun(self, pronoun: str, context: InterpretationContext) -> Optional[str]:
        """Resolve pronouns based on recent context"""
        if context.previous_interactions:
            last_interaction = context.previous_interactions[-1]
            # Simple heuristic: look for nouns in the last interaction
            words = last_interaction.split()
            nouns = [word for word in words if len(word) > 3 and word.isalpha()]
            if nouns:
                return nouns[-1]  # Last noun mentioned
        return None
    
    def resolve_location_reference(self, context: InterpretationContext) -> Optional[str]:
        """Resolve location references like 'there'"""
        if context.previous_interactions:
            # Look for location words in recent interactions
            location_words = ['home', 'office', 'store', 'restaurant', 'park', 'beach']
            for interaction in reversed(context.previous_interactions[-3:]):
                for location in location_words:
                    if location in interaction.lower():
                        return location
        return None
    
    def make_more_concise(self, text: str) -> str:
        """Make text more concise for focused users"""
        concise = text
        
        # Remove redundant words
        redundant_patterns = [
            (r'\bplease\s+', ''),
            (r'\bcan you\s+', ''),
            (r'\bi would like to\s+', ''),
            (r'\bi want to\s+', ''),
        ]
        
        for pattern, replacement in redundant_patterns:
            concise = re.sub(pattern, replacement, concise, flags=re.IGNORECASE)
        
        return concise.strip()
    
    def correct_likely_speech_errors(self, text: str, noise_level: float) -> str:
        """Correct likely speech recognition errors in noisy environments"""
        corrected = text
        
        # Common speech recognition errors in noise
        common_errors = {
            'call': 'call',  # Often misheard
            'set': 'set',
            'get': 'get',
            'to': 'to',
            'too': 'to',
            'two': 'to'
        }
        
        # Apply corrections with probability based on noise level
        for error, correction in common_errors.items():
            if error in corrected.lower() and np.random.random() < noise_level:
                corrected = re.sub(r'\b' + re.escape(error) + r'\b', correction,
                                 corrected, flags=re.IGNORECASE)
        
        return corrected
    
    def generate_improvement_suggestions(self, original: str, interpreted: str, 
                                       context: InterpretationContext) -> List[str]:
        """Generate suggestions for improving future interpretations"""
        suggestions = []
        
        if original.lower() == interpreted.lower():
            suggestions.append("Input was clear - no interpretation needed")
        else:
            suggestions.append(f"Interpreted '{original}' as '{interpreted}'")
        
        # Suggest personal shortcuts
        if len(original.split()) > 3:
            suggestions.append(f"Consider creating a shortcut for '{original}'")
        
        # Suggest vocabulary additions
        uncommon_words = [word for word in original.split() 
                         if len(word) > 6 and word.isalpha()]
        if uncommon_words:
            suggestions.append(f"Consider adding vocabulary mapping for: {', '.join(uncommon_words)}")
        
        return suggestions[:3]  # Limit to top 3 suggestions
    
    async def learn_from_feedback(self, result: InterpretationResult, 
                                success_score: float, ai_response_quality: float):
        """Learn from user feedback on interpretation quality"""
        
        # Add to training data
        training_example = {
            'original_input': result.original_input,
            'interpreted_input': result.interpreted_input,
            'context_factors': result.context_factors,
            'success_score': success_score,
            'ai_response_quality': ai_response_quality,
            'timestamp': result.timestamp
        }
        
        self.training_data.append(training_example)
        
        # Update personal patterns based on feedback
        if success_score > 0.8:  # Good interpretation
            await self.reinforce_successful_patterns(result)
        elif success_score < 0.4:  # Poor interpretation
            await self.learn_from_errors(result)
        
        # Trigger retraining if we have enough data
        if len(self.training_data) > 20 and not self.is_trained:
            await self.retrain_personal_models()
    
    async def reinforce_successful_patterns(self, result: InterpretationResult):
        """Reinforce patterns that led to successful interpretations"""
        
        # Extract successful vocabulary mappings
        original_words = set(result.original_input.lower().split())
        interpreted_words = set(result.interpreted_input.lower().split())
        
        new_words = interpreted_words - original_words
        if new_words:
            # These are words the interpreter added - reinforce them
            for orig_word in original_words:
                for new_word in new_words:
                    if self.words_are_related(orig_word, new_word):
                        self.profile.vocabulary_preferences[orig_word] = new_word
        
        # Reinforce context patterns
        task_type = result.context_factors.get('task_type')
        if task_type:
            if task_type not in self.profile.task_specializations:
                self.profile.task_specializations[task_type] = {}
            
            # Record successful pattern
            success_patterns = self.profile.task_specializations[task_type].get('success_patterns', [])
            success_patterns.append({
                'input_pattern': result.original_input,
                'output_pattern': result.interpreted_input,
                'context': result.context_factors
            })
            
            # Keep only recent patterns
            self.profile.task_specializations[task_type]['success_patterns'] = success_patterns[-10:]
    
    async def learn_from_errors(self, result: InterpretationResult):
        """Learn from interpretation errors"""
        
        # Record error pattern
        error_key = f"{result.original_input[:20]}_{result.context_factors.get('task_type')}"
        self.profile.error_patterns[error_key] = self.profile.error_patterns.get(error_key, 0) + 1
        
        # If error happens repeatedly, create correction rule
        if self.profile.error_patterns[error_key] > 2:
            # Add to speech patterns correction
            if 'common_errors' not in self.profile.speech_patterns:
                self.profile.speech_patterns['common_errors'] = {}
            
            self.profile.speech_patterns['common_errors'][result.original_input] = result.interpreted_input
    
    def words_are_related(self, word1: str, word2: str) -> bool:
        """Simple heuristic to check if words might be related"""
        # Very basic - could be enhanced with word embeddings
        if len(word1) < 3 or len(word2) < 3:
            return False
        
        # Check if one word contains the other
        if word1 in word2 or word2 in word1:
            return True
        
        # Check edit distance
        def edit_distance(s1, s2):
            if len(s1) > len(s2):
                s1, s2 = s2, s1
            distances = range(len(s1) + 1)
            for i2, c2 in enumerate(s2):
                distances_ = [i2 + 1]
                for i1, c1 in enumerate(s1):
                    if c1 == c2:
                        distances_.append(distances[i1])
                    else:
                        distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
                distances = distances_
            return distances[-1]
        
        return edit_distance(word1, word2) <= 2
    
    async def retrain_personal_models(self):
        """Retrain personal ML models with accumulated data"""
        if len(self.training_data) < 10:
            return
        
        logger.info(f"🧠 Retraining personal AI interpreter for user {self.user_id}")
        
        # Prepare training data
        X_features = []
        y_success = []
        
        for example in self.training_data:
            # Create feature vector
            features = self.create_feature_vector(example)
            X_features.append(features)
            y_success.append(example['success_score'])
        
        if len(X_features) > 5:
            X = np.array(X_features)
            y = np.array(y_success)
            
            try:
                # Train quality predictor
                if len(X) > 3:
                    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
                    self.quality_predictor.fit(X_train, y_train)
                    
                    if len(X_test) > 0:
                        predictions = self.quality_predictor.predict(X_test)
                        mse = mean_squared_error(y_test, predictions)
                        logger.info(f"Personal model MSE: {mse:.3f} for user {self.user_id}")
                
                self.is_trained = True
                self.last_training = datetime.now()
                self.profile.learning_confidence = min(1.0, self.profile.learning_confidence + 0.1)
                
            except Exception as e:
                logger.warning(f"Failed to train personal model for {self.user_id}: {e}")
    
    def create_feature_vector(self, example: Dict) -> np.ndarray:
        """Create feature vector for ML training"""
        features = []
        
        # Text features
        original_text = example['original_input']
        features.append(len(original_text.split()))  # Word count
        features.append(len(original_text))  # Character count
        features.append(original_text.count('?'))  # Question marks
        features.append(original_text.count('!'))  # Exclamation marks
        
        # Context features
        context = example['context_factors']
        features.append(hash(context.get('app_name', '')) % 100)  # App name hash
        features.append(hash(context.get('task_type', '')) % 100)  # Task type hash
        features.append(hash(context.get('user_state', '')) % 100)  # User state hash
        
        # Time features
        timestamp = example['timestamp']
        features.append(timestamp.hour)  # Hour of day
        features.append(timestamp.weekday())  # Day of week
        
        return np.array(features, dtype=float)


class UniversalAIInterpreterSystem:
    """System managing all personal AI interpreters"""
    
    def __init__(self, db_path: str = "/home/activeloguser/activelog/universal_interpreters.db"):
        self.db_path = db_path
        self.interpreters: Dict[str, PersonalAIInterpreter] = {}
        self.interpreter_cache = {}
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        self.initialize_database()
        self.load_interpreter_profiles()
    
    def initialize_database(self):
        """Initialize database for universal interpreter system"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_interpreter_profiles (
                    user_id TEXT PRIMARY KEY,
                    profile_data TEXT NOT NULL,
                    learning_confidence REAL DEFAULT 0.3,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    total_interactions INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 0.5
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS interpretation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    app_name TEXT NOT NULL,
                    original_input TEXT NOT NULL,
                    interpreted_input TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    success_score REAL,
                    ai_response_quality REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    context_data TEXT,
                    feedback_data TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS global_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT NOT NULL,
                    pattern_data TEXT NOT NULL,
                    usage_count INTEGER DEFAULT 1,
                    success_rate REAL DEFAULT 0.5,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    async def get_interpreter(self, user_id: str) -> PersonalAIInterpreter:
        """Get or create personal interpreter for user"""
        
        if user_id in self.interpreters:
            return self.interpreters[user_id]
        
        with self.lock:
            if user_id in self.interpreters:
                return self.interpreters[user_id]
            
            # Load from database
            profile = await self.load_interpreter_profile(user_id)
            interpreter = PersonalAIInterpreter(user_id, profile)
            
            self.interpreters[user_id] = interpreter
            return interpreter
    
    async def interpret_universal(self, user_id: str, raw_input: str, 
                                context: InterpretationContext) -> InterpretationResult:
        """Universal interpretation entry point"""
        
        interpreter = await self.get_interpreter(user_id)
        result = await interpreter.interpret(raw_input, context)
        
        # Store interpretation history
        await self.store_interpretation(result, context)
        
        return result
    
    async def provide_feedback(self, user_id: str, interpretation_id: str, 
                             success_score: float, ai_response_quality: float):
        """Provide feedback on interpretation quality"""
        
        interpreter = await self.get_interpreter(user_id)
        
        # Find the interpretation result
        matching_result = None
        for result in interpreter.recent_interactions:
            if str(hash(f"{result.original_input}_{result.timestamp}")) == interpretation_id:
                matching_result = result
                break
        
        if matching_result:
            await interpreter.learn_from_feedback(matching_result, success_score, ai_response_quality)
            await self.update_interpreter_profile(user_id, interpreter.profile)
            
            # Update database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    UPDATE interpretation_history 
                    SET success_score = ?, ai_response_quality = ?
                    WHERE user_id = ? AND original_input = ?
                ''', (success_score, ai_response_quality, user_id, matching_result.original_input))
                conn.commit()
    
    async def store_interpretation(self, result: InterpretationResult, context: InterpretationContext):
        """Store interpretation in history"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO interpretation_history 
                (user_id, app_name, original_input, interpreted_input, confidence, 
                 timestamp, context_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                context.user_id,
                context.app_name,
                result.original_input,
                result.interpreted_input,
                result.confidence,
                result.timestamp,
                json.dumps(result.context_factors)
            ))
            conn.commit()
    
    async def load_interpreter_profile(self, user_id: str) -> Optional[UserInterpretationProfile]:
        """Load interpreter profile from database"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT profile_data, learning_confidence
                FROM user_interpreter_profiles WHERE user_id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
        
        if row:
            try:
                profile_data = json.loads(row[0])
                profile = UserInterpretationProfile(
                    user_id=user_id,
                    speech_patterns=profile_data.get('speech_patterns', {}),
                    vocabulary_preferences=profile_data.get('vocabulary_preferences', {}),
                    context_adaptations=profile_data.get('context_adaptations', {}),
                    task_specializations=profile_data.get('task_specializations', {}),
                    learning_confidence=row[1],
                    personal_shortcuts=profile_data.get('personal_shortcuts', {}),
                    error_patterns=profile_data.get('error_patterns', {})
                )
                return profile
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse profile data for user {user_id}")
        
        return None
    
    async def update_interpreter_profile(self, user_id: str, profile: UserInterpretationProfile):
        """Update interpreter profile in database"""
        
        profile_data = {
            'speech_patterns': profile.speech_patterns,
            'vocabulary_preferences': profile.vocabulary_preferences,
            'context_adaptations': profile.context_adaptations,
            'task_specializations': profile.task_specializations,
            'personal_shortcuts': profile.personal_shortcuts,
            'error_patterns': profile.error_patterns
        }
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO user_interpreter_profiles
                (user_id, profile_data, learning_confidence)
                VALUES (?, ?, ?)
            ''', (
                user_id,
                json.dumps(profile_data),
                profile.learning_confidence
            ))
            conn.commit()
    
    def load_interpreter_profiles(self):
        """Load all interpreter profiles into memory"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT user_id FROM user_interpreter_profiles
            ''')
            
            user_ids = [row[0] for row in cursor.fetchall()]
        
        logger.info(f"🧠 Loaded {len(user_ids)} personal AI interpreter profiles")
    
    async def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """Get insights about user's interpretation patterns"""
        
        interpreter = await self.get_interpreter(user_id)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_interactions,
                    AVG(confidence) as avg_confidence,
                    AVG(success_score) as avg_success,
                    COUNT(DISTINCT app_name) as apps_used
                FROM interpretation_history 
                WHERE user_id = ?
            ''', (user_id,))
            
            stats = cursor.fetchone()
        
        return {
            'user_id': user_id,
            'total_interactions': stats[0] if stats else 0,
            'average_confidence': stats[1] if stats else 0.5,
            'success_rate': stats[2] if stats else 0.5,
            'apps_used': stats[3] if stats else 0,
            'learning_confidence': interpreter.profile.learning_confidence,
            'personal_shortcuts': len(interpreter.profile.personal_shortcuts),
            'vocabulary_mappings': len(interpreter.profile.vocabulary_preferences),
            'is_trained': interpreter.is_trained,
            'ecosystem_readiness': self.calculate_ecosystem_readiness(interpreter)
        }
    
    def calculate_ecosystem_readiness(self, interpreter: PersonalAIInterpreter) -> float:
        """Calculate how ready the interpreter is for ecosystem-wide tasks"""
        
        confidence = interpreter.profile.learning_confidence
        shortcuts = len(interpreter.profile.personal_shortcuts)
        vocabulary = len(interpreter.profile.vocabulary_preferences)
        specializations = len(interpreter.profile.task_specializations)
        
        readiness = confidence * 0.4  # Base from learning confidence
        readiness += min(0.3, shortcuts / 10 * 0.3)  # Up to 0.3 from shortcuts
        readiness += min(0.2, vocabulary / 20 * 0.2)  # Up to 0.2 from vocabulary
        readiness += min(0.1, specializations / 5 * 0.1)  # Up to 0.1 from specializations
        
        return min(1.0, readiness)


# Global universal AI interpreter system
universal_ai_interpreter = UniversalAIInterpreterSystem()

async def initialize_universal_interpreter():
    """Initialize the universal AI interpreter system"""
    logger.info("🧠 Initializing Universal AI Interpreter System...")
    return True

async def interpret_user_input(user_id: str, app_name: str, raw_input: str, 
                             task_type: str = 'text_input', **context_kwargs) -> InterpretationResult:
    """Universal function to interpret any user input across the ecosystem"""
    
    context = InterpretationContext(
        user_id=user_id,
        app_name=app_name,
        task_type=task_type,
        session_id=context_kwargs.get('session_id', 'default'),
        device_type=context_kwargs.get('device_type', 'desktop'),
        time_of_day=datetime.now().strftime('%H'),
        user_state=context_kwargs.get('user_state', 'focused'),
        previous_interactions=context_kwargs.get('previous_interactions', []),
        environment_noise=context_kwargs.get('environment_noise', 0.0),
        urgency_level=context_kwargs.get('urgency_level', 0.5)
    )
    
    return await universal_ai_interpreter.interpret_universal(user_id, raw_input, context)

async def provide_interpretation_feedback(user_id: str, interpretation_id: str, 
                                        success_score: float, ai_response_quality: float):
    """Provide feedback on interpretation quality"""
    await universal_ai_interpreter.provide_feedback(user_id, interpretation_id, 
                                                   success_score, ai_response_quality)