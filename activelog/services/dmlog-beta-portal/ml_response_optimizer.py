#!/usr/bin/env python3
"""
ML Response Quality Monitoring & Prompt Optimization System
Learns from user feedback to improve LLM outputs for D&D gaming
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import logging
import pickle
import os
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
import sqlite3

logger = logging.getLogger(__name__)

@dataclass
class ResponseQuality:
    user_input: str
    original_prompt: str
    optimized_prompt: str
    llm_model: str
    response: str
    quality_score: float
    user_feedback: Optional[str]
    session_id: str
    character: str
    timestamp: datetime
    response_time: float
    cost: float
    
    # Quality metrics
    engagement_score: float = 0.0
    coherence_score: float = 0.0
    character_consistency: float = 0.0
    relevance_score: float = 0.0
    creativity_score: float = 0.0

class MLResponseMonitor:
    """ML system to monitor and optimize LLM response quality"""
    
    def __init__(self, db_path: str = "dmlog_ml_responses.db"):
        self.db_path = db_path
        self.response_history = deque(maxlen=10000)
        self.quality_metrics = defaultdict(list)
        
        # ML models for different aspects
        self.quality_predictor = RandomForestRegressor(n_estimators=100, random_state=42)
        self.prompt_optimizer = None
        self.response_classifier = None
        
        # Feature extractors
        self.prompt_vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.response_vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        
        # Gaming-specific quality patterns
        self.quality_patterns = {
            'high_quality_indicators': [
                r'vivid description', r'atmospheric', r'immersive',
                r'stays in character', r'advances story', r'creative response',
                r'dramatic tension', r'compelling narrative'
            ],
            'low_quality_indicators': [
                r'generic response', r'out of character', r'repetitive',
                r'too short', r'confusing', r'inconsistent',
                r'breaks immersion', r'unhelpful'
            ],
            'character_consistency': [
                r'maintains voice', r'appropriate personality',
                r'consistent behavior', r'believable reactions'
            ]
        }
        
        self._init_database()
        self._load_models()
    
    def _init_database(self):
        """Initialize SQLite database for response tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS response_quality (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_input TEXT,
                original_prompt TEXT,
                optimized_prompt TEXT,
                llm_model TEXT,
                response TEXT,
                quality_score REAL,
                user_feedback TEXT,
                session_id TEXT,
                character TEXT,
                timestamp TEXT,
                response_time REAL,
                cost REAL,
                engagement_score REAL,
                coherence_score REAL,
                character_consistency REAL,
                relevance_score REAL,
                creativity_score REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prompt_optimizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_input TEXT,
                optimized_input TEXT,
                improvement_score REAL,
                llm_model TEXT,
                success_count INTEGER,
                total_count INTEGER,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_models(self):
        """Load pre-trained ML models if they exist"""
        models_dir = "ml_models"
        os.makedirs(models_dir, exist_ok=True)
        
        try:
            # Load quality predictor
            if os.path.exists(f"{models_dir}/quality_predictor.pkl"):
                with open(f"{models_dir}/quality_predictor.pkl", 'rb') as f:
                    self.quality_predictor = pickle.load(f)
                logger.info("✅ Loaded quality predictor model")
            
            # Load vectorizers
            if os.path.exists(f"{models_dir}/prompt_vectorizer.pkl"):
                with open(f"{models_dir}/prompt_vectorizer.pkl", 'rb') as f:
                    self.prompt_vectorizer = pickle.load(f)
                    
            if os.path.exists(f"{models_dir}/response_vectorizer.pkl"):
                with open(f"{models_dir}/response_vectorizer.pkl", 'rb') as f:
                    self.response_vectorizer = pickle.load(f)
                    
        except Exception as e:
            logger.warning(f"Model loading error: {e}")
    
    def analyze_response_quality(self, response_data: Dict[str, Any]) -> ResponseQuality:
        """Analyze the quality of an LLM response"""
        
        # Calculate individual quality scores
        engagement = self._calculate_engagement_score(response_data['response'], response_data['user_input'])
        coherence = self._calculate_coherence_score(response_data['response'])
        character_consistency = self._calculate_character_consistency(
            response_data['response'], response_data['character']
        )
        relevance = self._calculate_relevance_score(
            response_data['response'], response_data['user_input']
        )
        creativity = self._calculate_creativity_score(response_data['response'])
        
        # Overall quality score (weighted average)
        quality_score = (
            engagement * 0.25 +
            coherence * 0.20 +
            character_consistency * 0.20 +
            relevance * 0.20 +
            creativity * 0.15
        )
        
        quality = ResponseQuality(
            user_input=response_data['user_input'],
            original_prompt=response_data.get('original_prompt', ''),
            optimized_prompt=response_data.get('optimized_prompt', ''),
            llm_model=response_data['llm_model'],
            response=response_data['response'],
            quality_score=quality_score,
            user_feedback=response_data.get('user_feedback'),
            session_id=response_data['session_id'],
            character=response_data['character'],
            timestamp=datetime.now(),
            response_time=response_data.get('response_time', 0.0),
            cost=response_data.get('cost', 0.0),
            engagement_score=engagement,
            coherence_score=coherence,
            character_consistency=character_consistency,
            relevance_score=relevance,
            creativity_score=creativity
        )
        
        # Store in database
        self._store_response_quality(quality)
        
        # Add to recent history for real-time learning
        self.response_history.append(quality)
        
        return quality
    
    def _calculate_engagement_score(self, response: str, user_input: str) -> float:
        """Calculate how engaging the response is"""
        score = 0.5  # Base score
        
        # Length appropriateness (not too short, not too long)
        length = len(response)
        if 50 <= length <= 300:
            score += 0.2
        elif length < 20:
            score -= 0.3
        elif length > 500:
            score -= 0.1
        
        # Presence of descriptive elements
        descriptive_words = [
            'vivid', 'dramatic', 'mysterious', 'atmospheric', 'tense',
            'colorful', 'detailed', 'rich', 'immersive', 'captivating'
        ]
        
        response_lower = response.lower()
        descriptive_count = sum(1 for word in descriptive_words if word in response_lower)
        score += min(descriptive_count * 0.1, 0.3)
        
        # Dialogue and action indicators
        if '"' in response or "'" in response:  # Contains dialogue
            score += 0.1
        
        action_indicators = ['moves', 'looks', 'speaks', 'gestures', 'actions', 'does']
        action_count = sum(1 for indicator in action_indicators if indicator in response_lower)
        score += min(action_count * 0.05, 0.2)
        
        return min(score, 1.0)
    
    def _calculate_coherence_score(self, response: str) -> float:
        """Calculate how coherent and well-structured the response is"""
        score = 0.5
        
        # Sentence structure
        sentences = response.split('.')
        if len(sentences) > 1:
            score += 0.2
        
        # Grammar patterns (simple heuristics)
        if response.count(',') > 0:  # Uses commas appropriately
            score += 0.1
        
        # No obvious repetition
        words = response.lower().split()
        if len(set(words)) / max(len(words), 1) > 0.7:  # Good word diversity
            score += 0.2
        
        # Complete thoughts (ends with punctuation)
        if response.rstrip().endswith(('.', '!', '?', '"')):
            score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_character_consistency(self, response: str, character: str) -> float:
        """Calculate how well the response maintains character consistency"""
        character_traits = {
            'dm': ['guides', 'describes', 'narrative', 'story', 'world'],
            'tavern_keeper': ['ale', 'drinks', 'tavern', 'travelers', 'gold', 'room'],
            'wizard': ['magic', 'spell', 'arcane', 'ancient', 'wisdom', 'mystical'],
            'goblin': ['grax', 'shiny', 'fight', 'boss', 'scary', 'no like'],
            'narrator': ['scene', 'atmosphere', 'setting', 'environment', 'surroundings']
        }
        
        expected_traits = character_traits.get(character.lower(), [])
        if not expected_traits:
            return 0.7  # Default for unknown characters
        
        response_lower = response.lower()
        trait_matches = sum(1 for trait in expected_traits if trait in response_lower)
        
        consistency_score = min(trait_matches / len(expected_traits), 1.0)
        return max(consistency_score, 0.3)  # Minimum consistency
    
    def _calculate_relevance_score(self, response: str, user_input: str) -> float:
        """Calculate how relevant the response is to user input"""
        # Extract key words from user input
        user_words = set(re.findall(r'\w+', user_input.lower()))
        response_words = set(re.findall(r'\w+', response.lower()))
        
        # Remove common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'i', 'you', 'he', 'she', 'it', 'we', 'they'}
        user_keywords = user_words - stop_words
        response_keywords = response_words - stop_words
        
        if not user_keywords:
            return 0.5
        
        # Calculate overlap
        overlap = len(user_keywords & response_keywords)
        relevance = overlap / len(user_keywords)
        
        return min(relevance + 0.3, 1.0)  # Base relevance + overlap bonus
    
    def _calculate_creativity_score(self, response: str) -> float:
        """Calculate creativity and uniqueness of response"""
        score = 0.5
        
        # Creative language indicators
        creative_elements = [
            'suddenly', 'mysteriously', 'unexpectedly', 'strangely',
            'peculiar', 'unusual', 'remarkable', 'extraordinary'
        ]
        
        response_lower = response.lower()
        creative_count = sum(1 for element in creative_elements if element in response_lower)
        score += min(creative_count * 0.15, 0.3)
        
        # Unique word usage (less common words)
        words = response_lower.split()
        if len(words) > 0:
            avg_word_length = sum(len(word) for word in words) / len(words)
            if avg_word_length > 5:  # Longer words often indicate creativity
                score += 0.2
        
        return min(score, 1.0)
    
    def _store_response_quality(self, quality: ResponseQuality):
        """Store response quality data in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO response_quality 
            (user_input, original_prompt, optimized_prompt, llm_model, response,
             quality_score, user_feedback, session_id, character, timestamp,
             response_time, cost, engagement_score, coherence_score,
             character_consistency, relevance_score, creativity_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            quality.user_input, quality.original_prompt, quality.optimized_prompt,
            quality.llm_model, quality.response, quality.quality_score,
            quality.user_feedback, quality.session_id, quality.character,
            quality.timestamp.isoformat(), quality.response_time, quality.cost,
            quality.engagement_score, quality.coherence_score,
            quality.character_consistency, quality.relevance_score,
            quality.creativity_score
        ))
        
        conn.commit()
        conn.close()


class PromptOptimizer:
    """ML-powered prompt optimizer that learns to rewrite user inputs"""
    
    def __init__(self, response_monitor: MLResponseMonitor):
        self.response_monitor = response_monitor
        self.optimization_patterns = {}
        self.success_history = defaultdict(list)
        
        # Gaming-specific prompt templates
        self.gaming_templates = {
            'combat': {
                'patterns': [r'\b(attack|fight|battle|combat)\b'],
                'optimization': 'In combat, describe your action vividly: {original_input}. What is your tactical approach?'
            },
            'exploration': {
                'patterns': [r'\b(look|search|explore|examine|investigate)\b'],
                'optimization': 'As you explore, {original_input}. What specific details catch your attention?'
            },
            'dialogue': {
                'patterns': [r'\b(say|talk|speak|ask|tell)\b'],
                'optimization': 'In character dialogue: {original_input}. How does your character express this?'
            },
            'magic': {
                'patterns': [r'\b(cast|spell|magic|enchant|summon)\b'],
                'optimization': 'Casting magic: {original_input}. Describe the mystical energy and effects.'
            },
            'social': {
                'patterns': [r'\b(persuade|intimidate|deceive|charm|negotiate)\b'],
                'optimization': 'In social interaction: {original_input}. What is your character\'s demeanor and approach?'
            }
        }
        
        self._load_optimization_patterns()
    
    def _load_optimization_patterns(self):
        """Load learned optimization patterns from database"""
        try:
            conn = sqlite3.connect(self.response_monitor.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT original_input, optimized_input, improvement_score, llm_model,
                       success_count, total_count
                FROM prompt_optimizations
                WHERE improvement_score > 0.1
                ORDER BY improvement_score DESC
            ''')
            
            results = cursor.fetchall()
            
            for row in results:
                original, optimized, improvement, model, success, total = row
                if total > 0:
                    success_rate = success / total
                    if success_rate > 0.6:  # Only use patterns with >60% success rate
                        self.optimization_patterns[original] = {
                            'optimized': optimized,
                            'improvement': improvement,
                            'model': model,
                            'success_rate': success_rate
                        }
            
            logger.info(f"Loaded {len(self.optimization_patterns)} optimization patterns")
            conn.close()
            
        except Exception as e:
            logger.warning(f"Failed to load optimization patterns: {e}")
    
    def optimize_user_input(self, user_input: str, character: str, llm_model: str) -> Tuple[str, float]:
        """
        Optimize user input for better LLM response quality
        Returns (optimized_input, confidence_score)
        """
        
        # Check for exact matches in learned patterns
        if user_input in self.optimization_patterns:
            pattern = self.optimization_patterns[user_input]
            if pattern['model'] == llm_model or pattern['model'] == 'universal':
                return pattern['optimized'], pattern['success_rate']
        
        # Apply gaming-specific templates
        optimized_input = self._apply_gaming_templates(user_input, character)
        
        # ML-based optimization (if we have enough training data)
        ml_optimized = self._ml_optimize_input(user_input, character, llm_model)
        
        if ml_optimized:
            return ml_optimized
        
        # Return template-optimized input with moderate confidence
        if optimized_input != user_input:
            return optimized_input, 0.7
        
        # No optimization needed
        return user_input, 1.0
    
    def _apply_gaming_templates(self, user_input: str, character: str) -> str:
        """Apply gaming-specific prompt templates"""
        user_lower = user_input.lower()
        
        # Find matching template
        for category, template_data in self.gaming_templates.items():
            for pattern in template_data['patterns']:
                if re.search(pattern, user_lower):
                    # Apply template
                    optimized = template_data['optimization'].format(original_input=user_input)
                    
                    # Add character-specific context
                    if character == 'dm':
                        optimized += " How does this affect the story?"
                    elif character in ['tavern_keeper', 'wizard', 'goblin']:
                        optimized += f" How does the {character} react?"
                    
                    return optimized
        
        return user_input
    
    def _ml_optimize_input(self, user_input: str, character: str, llm_model: str) -> Optional[Tuple[str, float]]:
        """Use ML to optimize input based on historical performance"""
        
        # Need sufficient training data
        if len(self.response_monitor.response_history) < 50:
            return None
        
        # Find similar successful inputs
        similar_inputs = self._find_similar_successful_inputs(user_input, character, llm_model)
        
        if similar_inputs:
            # Use the most successful similar optimization
            best_optimization = max(similar_inputs, key=lambda x: x['quality_score'])
            
            # Adapt the successful pattern
            adapted_input = self._adapt_optimization_pattern(
                user_input, 
                best_optimization['original_input'],
                best_optimization['optimized_prompt']
            )
            
            return adapted_input, best_optimization['quality_score']
        
        return None
    
    def _find_similar_successful_inputs(self, user_input: str, character: str, llm_model: str) -> List[Dict]:
        """Find similar inputs that produced high-quality responses"""
        similar_inputs = []
        
        user_words = set(user_input.lower().split())
        
        for quality_data in self.response_monitor.response_history:
            if (quality_data.character == character and 
                quality_data.llm_model == llm_model and
                quality_data.quality_score > 0.7):
                
                input_words = set(quality_data.user_input.lower().split())
                similarity = len(user_words & input_words) / len(user_words | input_words)
                
                if similarity > 0.3:  # 30% word overlap
                    similar_inputs.append({
                        'original_input': quality_data.user_input,
                        'optimized_prompt': quality_data.optimized_prompt,
                        'quality_score': quality_data.quality_score,
                        'similarity': similarity
                    })
        
        return similar_inputs
    
    def _adapt_optimization_pattern(self, current_input: str, successful_input: str, successful_optimization: str) -> str:
        """Adapt a successful optimization pattern to current input"""
        
        # Simple pattern adaptation - replace key terms
        current_words = current_input.split()
        successful_words = successful_input.split()
        
        adapted_optimization = successful_optimization
        
        # Replace similar words
        for i, word in enumerate(successful_words):
            if i < len(current_words) and word.lower() != current_words[i].lower():
                adapted_optimization = adapted_optimization.replace(word, current_words[i])
        
        return adapted_optimization
    
    def record_optimization_success(self, original_input: str, optimized_input: str, 
                                  quality_improvement: float, llm_model: str):
        """Record the success of an optimization for learning"""
        
        conn = sqlite3.connect(self.response_monitor.db_path)
        cursor = conn.cursor()
        
        # Check if this optimization exists
        cursor.execute('''
            SELECT success_count, total_count FROM prompt_optimizations
            WHERE original_input = ? AND optimized_input = ? AND llm_model = ?
        ''', (original_input, optimized_input, llm_model))
        
        result = cursor.fetchone()
        
        if result:
            # Update existing record
            success_count, total_count = result
            new_success = success_count + (1 if quality_improvement > 0 else 0)
            new_total = total_count + 1
            
            cursor.execute('''
                UPDATE prompt_optimizations 
                SET success_count = ?, total_count = ?, improvement_score = ?, updated_at = ?
                WHERE original_input = ? AND optimized_input = ? AND llm_model = ?
            ''', (new_success, new_total, quality_improvement, datetime.now().isoformat(),
                  original_input, optimized_input, llm_model))
        else:
            # Create new record
            cursor.execute('''
                INSERT INTO prompt_optimizations 
                (original_input, optimized_input, improvement_score, llm_model,
                 success_count, total_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (original_input, optimized_input, quality_improvement, llm_model,
                  1 if quality_improvement > 0 else 0, 1,
                  datetime.now().isoformat(), datetime.now().isoformat()))
        
        conn.commit()
        conn.close()


class AdaptiveLLMSystem:
    """Complete adaptive system that monitors quality and optimizes prompts"""
    
    def __init__(self):
        self.response_monitor = MLResponseMonitor()
        self.prompt_optimizer = PromptOptimizer(self.response_monitor)
        self.model_performance = defaultdict(lambda: {'total_score': 0.0, 'count': 0})
        
    async def process_gaming_request(self, user_input: str, character: str, 
                                   llm_model: str, session_id: str) -> Dict[str, Any]:
        """Process a gaming request with ML optimization"""
        
        # Step 1: Optimize user input
        optimized_input, confidence = self.prompt_optimizer.optimize_user_input(
            user_input, character, llm_model
        )
        
        # Step 2: Generate response (this would call your tiered LLM system)
        response_data = {
            'user_input': user_input,
            'original_prompt': user_input,
            'optimized_prompt': optimized_input,
            'character': character,
            'llm_model': llm_model,
            'session_id': session_id,
            'response': '',  # Will be filled by LLM
            'response_time': 0.0,
            'cost': 0.0
        }
        
        return {
            'optimized_input': optimized_input,
            'optimization_confidence': confidence,
            'response_data_template': response_data
        }
    
    def record_response_quality(self, response_data: Dict[str, Any], 
                              user_feedback: Optional[str] = None) -> float:
        """Record and analyze response quality"""
        
        if user_feedback:
            response_data['user_feedback'] = user_feedback
        
        # Analyze quality
        quality = self.response_monitor.analyze_response_quality(response_data)
        
        # Update model performance tracking
        model = response_data['llm_model']
        self.model_performance[model]['total_score'] += quality.quality_score
        self.model_performance[model]['count'] += 1
        
        # Record optimization success if this was an optimized prompt
        if response_data['optimized_prompt'] != response_data['user_input']:
            # Compare with baseline (would need baseline quality data)
            quality_improvement = quality.quality_score - 0.5  # Simplified
            
            self.prompt_optimizer.record_optimization_success(
                response_data['user_input'],
                response_data['optimized_prompt'],
                quality_improvement,
                response_data['llm_model']
            )
        
        logger.info(f"Response quality: {quality.quality_score:.2f} for {model}")
        
        return quality.quality_score
    
    def get_model_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for all models"""
        stats = {}
        
        for model, data in self.model_performance.items():
            if data['count'] > 0:
                stats[model] = {
                    'average_quality': data['total_score'] / data['count'],
                    'total_requests': data['count'],
                    'model_rank': 0  # Will be calculated
                }
        
        # Rank models by performance
        sorted_models = sorted(stats.items(), key=lambda x: x[1]['average_quality'], reverse=True)
        for i, (model, data) in enumerate(sorted_models):
            stats[model]['model_rank'] = i + 1
        
        return stats
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get recommendations for improving response quality"""
        recommendations = []
        
        # Analyze recent low-quality responses
        recent_responses = list(self.response_monitor.response_history)[-50:]
        low_quality = [r for r in recent_responses if r.quality_score < 0.6]
        
        if len(low_quality) > len(recent_responses) * 0.3:  # >30% low quality
            recommendations.append({
                'type': 'quality_alert',
                'message': 'Response quality has declined recently',
                'suggestion': 'Consider enabling Game Master LLM for better responses'
            })
        
        # Model-specific recommendations
        model_stats = self.get_model_performance_stats()
        for model, stats in model_stats.items():
            if stats['average_quality'] < 0.5:
                recommendations.append({
                    'type': 'model_performance',
                    'message': f'{model} showing low performance',
                    'suggestion': f'Consider switching to higher-ranked model for better quality'
                })
        
        return recommendations

# Global adaptive system
adaptive_llm_system = AdaptiveLLMSystem()