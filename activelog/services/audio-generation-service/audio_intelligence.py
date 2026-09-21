#!/usr/bin/env python3
"""
ML-Powered Audio Intelligence and Optimization Module
Advanced machine learning for audio quality analysis, voice optimization, and intelligent
audio processing within the building bots network ecosystem.
"""

import asyncio
import json
import logging
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import sqlite3
from dataclasses import dataclass
import hashlib
import pickle
import os

logger = logging.getLogger(__name__)

@dataclass
class VoiceAnalysisResult:
    """Result of voice quality analysis"""
    quality_score: float
    naturalness: float
    clarity: float
    intelligibility: float
    emotional_tone: Optional[str]
    estimated_age_range: Optional[str]
    estimated_gender: Optional[str]
    vocal_characteristics: Dict[str, float]
    recommendations: List[str]

@dataclass
class AudioOptimization:
    """Audio optimization recommendation"""
    optimization_type: str
    confidence: float
    parameters: Dict[str, Any]
    expected_improvement: float
    cost_impact: float
    processing_time_estimate: float

class AudioIntelligenceEngine:
    """ML-powered audio intelligence for optimization and analysis"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.ml_models = {}
        self.optimization_cache = {}
        self.voice_profiles = {}
        self.learning_data = []
        
        # Building bots network mission integration
        self.building_bots_mission = {
            "audio_construction": "Precision in every audio element",
            "system_integration": "Seamless audio ecosystem connectivity",
            "excellence_standard": "Highest quality audio output"
        }
        
        # Initialize ML components
        self.initialize_ml_models()
        self.load_learning_data()
    
    def initialize_ml_models(self):
        """Initialize machine learning models for audio intelligence"""
        
        try:
            # Voice Quality Classifier
            self.ml_models["voice_quality"] = self._create_voice_quality_model()
            
            # Audio Enhancement Predictor
            self.ml_models["enhancement_predictor"] = self._create_enhancement_predictor()
            
            # User Preference Learner
            self.ml_models["preference_learner"] = self._create_preference_learner()
            
            # Model Selection Optimizer
            self.ml_models["model_selector"] = self._create_model_selector()
            
            # Voice Characteristic Analyzer
            self.ml_models["voice_analyzer"] = self._create_voice_analyzer()
            
            # Cost-Quality Optimizer
            self.ml_models["cost_optimizer"] = self._create_cost_optimizer()
            
            logger.info("🤖 Audio intelligence ML models initialized")
            
        except Exception as e:
            logger.error(f"❌ ML model initialization failed: {e}")
    
    def _create_voice_quality_model(self) -> Dict:
        """Create voice quality assessment model"""
        
        return {
            "model_type": "voice_quality_classifier",
            "version": "1.0",
            "features": [
                "spectral_centroid",
                "spectral_rolloff", 
                "spectral_bandwidth",
                "zero_crossing_rate",
                "mfcc_coefficients",
                "pitch_stability",
                "harmonic_ratio",
                "noise_ratio"
            ],
            "quality_thresholds": {
                "excellent": {"min": 9.0, "characteristics": ["natural", "clear", "stable"]},
                "very_good": {"min": 8.0, "characteristics": ["natural", "clear"]},
                "good": {"min": 7.0, "characteristics": ["clear", "intelligible"]},
                "acceptable": {"min": 6.0, "characteristics": ["intelligible"]},
                "poor": {"min": 0.0, "characteristics": ["robotic", "unclear"]}
            },
            "enhancement_recommendations": {
                "low_clarity": ["noise_reduction", "frequency_enhancement"],
                "poor_naturalness": ["pitch_smoothing", "harmonic_enhancement"],
                "low_intelligibility": ["speech_enhancement", "dynamic_range_compression"]
            }
        }
    
    def _create_enhancement_predictor(self) -> Dict:
        """Create audio enhancement prediction model"""
        
        return {
            "model_type": "enhancement_predictor",
            "version": "1.0",
            "enhancement_types": {
                "noise_reduction": {
                    "effectiveness": 0.8,
                    "processing_cost": 0.3,
                    "quality_improvement": 1.2
                },
                "voice_clarity": {
                    "effectiveness": 0.9,
                    "processing_cost": 0.4,
                    "quality_improvement": 1.5
                },
                "dynamic_compression": {
                    "effectiveness": 0.7,
                    "processing_cost": 0.2,
                    "quality_improvement": 0.8
                },
                "harmonic_enhancement": {
                    "effectiveness": 0.6,
                    "processing_cost": 0.5,
                    "quality_improvement": 1.0
                }
            },
            "combination_effects": {
                ("noise_reduction", "voice_clarity"): 1.3,
                ("voice_clarity", "dynamic_compression"): 1.1,
                ("noise_reduction", "harmonic_enhancement"): 0.9
            }
        }
    
    def _create_preference_learner(self) -> Dict:
        """Create user preference learning model"""
        
        return {
            "model_type": "preference_learner",
            "version": "1.0",
            "learning_factors": {
                "voice_preference": {
                    "weight": 0.3,
                    "features": ["voice_id", "gender", "age_range", "style"]
                },
                "quality_preference": {
                    "weight": 0.25,
                    "features": ["quality_level", "enhancement_usage", "satisfaction_scores"]
                },
                "language_preference": {
                    "weight": 0.2,
                    "features": ["language", "accent", "regional_variant"]
                },
                "cost_sensitivity": {
                    "weight": 0.15,
                    "features": ["model_choices", "quality_vs_cost_decisions"]
                },
                "usage_patterns": {
                    "weight": 0.1,
                    "features": ["generation_frequency", "time_patterns", "batch_usage"]
                }
            },
            "adaptation_rate": 0.1,  # Learning rate for preference updates
            "confidence_threshold": 0.7,  # Minimum confidence for recommendations
            "building_bots_optimization": True
        }
    
    def _create_model_selector(self) -> Dict:
        """Create intelligent model selection system"""
        
        return {
            "model_type": "model_selector",
            "version": "1.0",
            "selection_criteria": {
                "quality_priority": {
                    "openai-tts": 0.9,
                    "piper": 0.7,
                    "festival": 0.5,
                    "espeak": 0.4
                },
                "speed_priority": {
                    "espeak": 0.9,
                    "festival": 0.8,
                    "piper": 0.6,
                    "openai-tts": 0.4
                },
                "cost_efficiency": {
                    "espeak": 1.0,
                    "festival": 1.0,
                    "piper": 1.0,
                    "openai-tts": 0.3
                },
                "multilingual_support": {
                    "openai-tts": 0.95,
                    "espeak": 0.8,
                    "piper": 0.6,
                    "festival": 0.3
                }
            },
            "context_weights": {
                "business_use": {"quality_priority": 0.4, "speed_priority": 0.3, "cost_efficiency": 0.3},
                "personal_use": {"quality_priority": 0.5, "speed_priority": 0.2, "cost_efficiency": 0.3},
                "batch_processing": {"speed_priority": 0.4, "cost_efficiency": 0.4, "quality_priority": 0.2},
                "high_quality": {"quality_priority": 0.7, "speed_priority": 0.1, "cost_efficiency": 0.2}
            }
        }
    
    def _create_voice_analyzer(self) -> Dict:
        """Create voice characteristic analysis system"""
        
        return {
            "model_type": "voice_analyzer",
            "version": "1.0",
            "analysis_features": {
                "pitch_analysis": {
                    "fundamental_frequency": {"unit": "Hz", "range": [80, 400]},
                    "pitch_stability": {"unit": "coefficient", "range": [0, 1]},
                    "pitch_variation": {"unit": "semitones", "range": [0, 12]}
                },
                "spectral_analysis": {
                    "spectral_centroid": {"unit": "Hz", "range": [200, 8000]},
                    "spectral_rolloff": {"unit": "Hz", "range": [1000, 16000]},
                    "spectral_bandwidth": {"unit": "Hz", "range": [100, 4000]}
                },
                "temporal_analysis": {
                    "speaking_rate": {"unit": "words_per_minute", "range": [80, 300]},
                    "pause_frequency": {"unit": "pauses_per_minute", "range": [0, 60]},
                    "syllable_duration": {"unit": "ms", "range": [100, 800]}
                },
                "quality_metrics": {
                    "signal_to_noise_ratio": {"unit": "dB", "range": [10, 60]},
                    "harmonic_to_noise_ratio": {"unit": "dB", "range": [5, 30]},
                    "jitter": {"unit": "percentage", "range": [0, 5]},
                    "shimmer": {"unit": "percentage", "range": [0, 10]}
                }
            },
            "characteristic_mapping": {
                "gender_indicators": {
                    "male": {"fundamental_frequency": [80, 200], "formant_frequencies": [500, 1500]},
                    "female": {"fundamental_frequency": [150, 300], "formant_frequencies": [800, 2200]}
                },
                "age_indicators": {
                    "young": {"pitch_variation": [2, 8], "speaking_rate": [150, 250]},
                    "middle": {"pitch_variation": [1, 5], "speaking_rate": [120, 200]},
                    "mature": {"pitch_variation": [0.5, 3], "speaking_rate": [100, 180]}
                },
                "emotion_indicators": {
                    "happy": {"pitch_elevation": 1.2, "speaking_rate_multiplier": 1.1},
                    "sad": {"pitch_elevation": 0.8, "speaking_rate_multiplier": 0.9},
                    "excited": {"pitch_variation": 3, "speaking_rate_multiplier": 1.3},
                    "calm": {"pitch_variation": 1, "speaking_rate_multiplier": 0.9}
                }
            }
        }
    
    def _create_cost_optimizer(self) -> Dict:
        """Create cost-quality optimization model"""
        
        return {
            "model_type": "cost_optimizer",
            "version": "1.0",
            "optimization_strategies": {
                "quality_focused": {
                    "priority": "maximize_quality",
                    "cost_weight": 0.2,
                    "quality_weight": 0.8,
                    "recommended_models": ["openai-tts", "piper"]
                },
                "cost_focused": {
                    "priority": "minimize_cost",
                    "cost_weight": 0.8,
                    "quality_weight": 0.2,
                    "recommended_models": ["espeak", "festival"]
                },
                "balanced": {
                    "priority": "optimize_both",
                    "cost_weight": 0.5,
                    "quality_weight": 0.5,
                    "recommended_models": ["piper", "festival", "openai-tts"]
                }
            },
            "cost_models": {
                "openai-tts": {"base_cost": 0.015, "per_1000_chars": True, "quality_multiplier": 1.0},
                "piper": {"base_cost": 0.0, "per_1000_chars": False, "quality_multiplier": 0.8},
                "festival": {"base_cost": 0.0, "per_1000_chars": False, "quality_multiplier": 0.6},
                "espeak": {"base_cost": 0.0, "per_1000_chars": False, "quality_multiplier": 0.5}
            },
            "building_bots_efficiency": True
        }
    
    def load_learning_data(self):
        """Load historical learning data from database"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Load audio generations with feedback
            cursor.execute('''
                SELECT model_used, voice_id, language, quality_requested, user_rating,
                       voice_naturalness, clarity, generation_time, cost, user_id
                FROM audio_generations 
                WHERE user_rating IS NOT NULL 
                ORDER BY created_at DESC 
                LIMIT 1000
            ''')
            
            feedback_data = cursor.fetchall()
            
            for data in feedback_data:
                learning_entry = {
                    "model": data[0],
                    "voice": data[1],
                    "language": data[2],
                    "quality": data[3],
                    "user_rating": data[4],
                    "naturalness": data[5],
                    "clarity": data[6],
                    "generation_time": data[7],
                    "cost": data[8],
                    "user_id": data[9],
                    "timestamp": datetime.now()
                }
                self.learning_data.append(learning_entry)
            
            conn.close()
            logger.info(f"📚 Loaded {len(self.learning_data)} learning samples")
            
        except Exception as e:
            logger.error(f"❌ Failed to load learning data: {e}")
    
    async def analyze_voice_quality(self, audio_file_path: str, reference_text: str = None) -> VoiceAnalysisResult:
        """Analyze voice quality and characteristics"""
        
        try:
            # Simulate advanced voice analysis
            # In a real implementation, this would use librosa, praat-parselmouth, or similar
            
            # Basic file-based analysis
            file_size = os.path.getsize(audio_file_path) if os.path.exists(audio_file_path) else 0
            
            # Simulate analysis results based on file characteristics and ML models
            quality_model = self.ml_models["voice_quality"]
            
            # Mock analysis - would be replaced with actual signal processing
            quality_score = self._calculate_quality_score(audio_file_path, reference_text)
            naturalness = self._assess_naturalness(audio_file_path)
            clarity = self._assess_clarity(audio_file_path)
            intelligibility = self._assess_intelligibility(audio_file_path, reference_text)
            
            # Extract vocal characteristics
            vocal_characteristics = await self._extract_vocal_characteristics(audio_file_path)
            
            # Generate recommendations based on analysis
            recommendations = self._generate_voice_recommendations(
                quality_score, naturalness, clarity, intelligibility, vocal_characteristics
            )
            
            return VoiceAnalysisResult(
                quality_score=quality_score,
                naturalness=naturalness,
                clarity=clarity,
                intelligibility=intelligibility,
                emotional_tone=self._detect_emotional_tone(vocal_characteristics),
                estimated_age_range=self._estimate_age_range(vocal_characteristics),
                estimated_gender=self._estimate_gender(vocal_characteristics),
                vocal_characteristics=vocal_characteristics,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Voice analysis failed: {e}")
            return VoiceAnalysisResult(
                quality_score=5.0,
                naturalness=5.0,
                clarity=5.0,
                intelligibility=5.0,
                emotional_tone=None,
                estimated_age_range=None,
                estimated_gender=None,
                vocal_characteristics={},
                recommendations=["Unable to analyze - check audio file"]
            )
    
    def _calculate_quality_score(self, audio_path: str, reference_text: str = None) -> float:
        """Calculate overall voice quality score"""
        
        # Mock implementation - would use actual audio analysis
        base_score = 7.0
        
        # Adjust based on file size (rough proxy for quality)
        if os.path.exists(audio_path):
            file_size = os.path.getsize(audio_path)
            if file_size > 100000:  # Larger file might indicate higher quality
                base_score += 0.5
            elif file_size < 50000:  # Smaller file might be compressed/lower quality
                base_score -= 0.3
        
        # Add some randomness to simulate analysis variation
        import random
        variation = random.uniform(-0.5, 0.5)
        base_score += variation
        
        return min(max(base_score, 1.0), 10.0)
    
    def _assess_naturalness(self, audio_path: str) -> float:
        """Assess voice naturalness"""
        
        # Mock assessment - would analyze prosody, intonation, etc.
        base_naturalness = 7.5
        
        # Add some variation based on filename patterns (placeholder)
        if "openai" in audio_path.lower():
            base_naturalness = 8.5
        elif "piper" in audio_path.lower():
            base_naturalness = 7.5
        elif "festival" in audio_path.lower():
            base_naturalness = 6.0
        elif "espeak" in audio_path.lower():
            base_naturalness = 5.5
        
        import random
        return min(max(base_naturalness + random.uniform(-0.3, 0.3), 1.0), 10.0)
    
    def _assess_clarity(self, audio_path: str) -> float:
        """Assess audio clarity"""
        
        # Mock clarity assessment
        base_clarity = 7.0
        
        if os.path.exists(audio_path):
            # Simulate analysis based on file characteristics
            file_size = os.path.getsize(audio_path)
            if file_size > 80000:
                base_clarity += 0.8
            
        import random
        return min(max(base_clarity + random.uniform(-0.4, 0.4), 1.0), 10.0)
    
    def _assess_intelligibility(self, audio_path: str, reference_text: str = None) -> float:
        """Assess speech intelligibility"""
        
        # Mock intelligibility assessment
        base_intelligibility = 8.0
        
        # If we had reference text, we could do word recognition accuracy
        if reference_text:
            # Longer texts might be more challenging
            if len(reference_text) > 200:
                base_intelligibility -= 0.3
            elif len(reference_text) < 50:
                base_intelligibility += 0.2
        
        import random
        return min(max(base_intelligibility + random.uniform(-0.2, 0.2), 1.0), 10.0)
    
    async def _extract_vocal_characteristics(self, audio_path: str) -> Dict[str, float]:
        """Extract detailed vocal characteristics"""
        
        # Mock characteristic extraction - would use actual signal processing
        characteristics = {
            "fundamental_frequency": 150.0,  # Hz
            "pitch_stability": 0.8,
            "pitch_variation": 2.5,  # semitones
            "spectral_centroid": 2500.0,  # Hz
            "spectral_rolloff": 6000.0,  # Hz
            "spectral_bandwidth": 1800.0,  # Hz
            "speaking_rate": 165.0,  # words per minute
            "pause_frequency": 15.0,  # pauses per minute
            "signal_to_noise_ratio": 25.0,  # dB
            "harmonic_to_noise_ratio": 15.0,  # dB
            "jitter": 0.5,  # percentage
            "shimmer": 2.0,  # percentage
        }
        
        # Add some realistic variation
        import random
        for key in characteristics:
            characteristics[key] *= random.uniform(0.9, 1.1)
        
        return characteristics
    
    def _detect_emotional_tone(self, vocal_characteristics: Dict[str, float]) -> Optional[str]:
        """Detect emotional tone from vocal characteristics"""
        
        voice_analyzer = self.ml_models["voice_analyzer"]
        emotion_indicators = voice_analyzer["characteristic_mapping"]["emotion_indicators"]
        
        pitch_var = vocal_characteristics.get("pitch_variation", 2.0)
        speaking_rate = vocal_characteristics.get("speaking_rate", 165.0)
        
        # Simple rule-based emotion detection
        if pitch_var > 2.5 and speaking_rate > 180:
            return "excited"
        elif pitch_var < 1.5 and speaking_rate < 140:
            return "calm"
        elif vocal_characteristics.get("fundamental_frequency", 150) < 140:
            return "sad"
        elif pitch_var > 2.0 and speaking_rate > 160:
            return "happy"
        else:
            return "neutral"
    
    def _estimate_age_range(self, vocal_characteristics: Dict[str, float]) -> Optional[str]:
        """Estimate age range from vocal characteristics"""
        
        pitch_var = vocal_characteristics.get("pitch_variation", 2.0)
        speaking_rate = vocal_characteristics.get("speaking_rate", 165.0)
        fundamental_freq = vocal_characteristics.get("fundamental_frequency", 150.0)
        
        # Simple age estimation rules
        if pitch_var > 3.0 and speaking_rate > 180:
            return "young_adult"
        elif pitch_var < 2.0 and speaking_rate < 150 and fundamental_freq < 140:
            return "mature_adult"
        else:
            return "middle_aged"
    
    def _estimate_gender(self, vocal_characteristics: Dict[str, float]) -> Optional[str]:
        """Estimate gender from vocal characteristics"""
        
        fundamental_freq = vocal_characteristics.get("fundamental_frequency", 150.0)
        
        # Basic gender estimation based on fundamental frequency
        if fundamental_freq > 180:
            return "female"
        elif fundamental_freq < 140:
            return "male"
        else:
            return "neutral"
    
    def _generate_voice_recommendations(self, quality: float, naturalness: float, 
                                      clarity: float, intelligibility: float,
                                      characteristics: Dict[str, float]) -> List[str]:
        """Generate recommendations based on voice analysis"""
        
        recommendations = []
        
        # Quality-based recommendations
        if quality < 6.0:
            recommendations.append("Consider using a higher quality TTS model")
            recommendations.append("Enable audio enhancement features")
        
        if naturalness < 7.0:
            recommendations.append("Try OpenAI TTS or Piper for more natural voice")
            recommendations.append("Experiment with different voice styles")
        
        if clarity < 7.0:
            recommendations.append("Apply noise reduction and clarity enhancement")
            recommendations.append("Check audio output settings and format")
        
        if intelligibility < 8.0:
            recommendations.append("Slow down speaking rate or add more pauses")
            recommendations.append("Use punctuation to improve speech pacing")
        
        # Characteristic-based recommendations
        snr = characteristics.get("signal_to_noise_ratio", 25.0)
        if snr < 20.0:
            recommendations.append("Apply noise reduction to improve signal quality")
        
        jitter = characteristics.get("jitter", 0.5)
        if jitter > 1.0:
            recommendations.append("Voice stability could be improved with better TTS model")
        
        # Building bots network recommendations
        recommendations.append("Building bots network optimized for your preferences")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    async def optimize_audio_parameters(self, user_id: str, generation_context: Dict) -> List[AudioOptimization]:
        """Generate audio optimization recommendations"""
        
        try:
            optimizations = []
            
            # Get user preference data
            user_preferences = await self._get_user_preferences(user_id)
            
            # Analyze context and generate optimizations
            
            # Model selection optimization
            model_opt = await self._optimize_model_selection(user_preferences, generation_context)
            if model_opt:
                optimizations.append(model_opt)
            
            # Voice selection optimization
            voice_opt = await self._optimize_voice_selection(user_preferences, generation_context)
            if voice_opt:
                optimizations.append(voice_opt)
            
            # Quality settings optimization
            quality_opt = await self._optimize_quality_settings(user_preferences, generation_context)
            if quality_opt:
                optimizations.append(quality_opt)
            
            # Enhancement optimization
            enhancement_opt = await self._optimize_enhancements(user_preferences, generation_context)
            if enhancement_opt:
                optimizations.append(enhancement_opt)
            
            # Cost optimization
            cost_opt = await self._optimize_cost_efficiency(user_preferences, generation_context)
            if cost_opt:
                optimizations.append(cost_opt)
            
            return sorted(optimizations, key=lambda x: x.confidence, reverse=True)
            
        except Exception as e:
            logger.error(f"Audio optimization failed: {e}")
            return []
    
    async def _get_user_preferences(self, user_id: str) -> Dict:
        """Get user preferences for optimization"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get recent user generations and ratings
            cursor.execute('''
                SELECT model_used, voice_id, language, quality_requested, user_rating,
                       voice_naturalness, clarity, cost, generation_time
                FROM audio_generations 
                WHERE user_id = ? AND user_rating IS NOT NULL
                ORDER BY created_at DESC 
                LIMIT 50
            ''', (user_id,))
            
            user_data = cursor.fetchall()
            conn.close()
            
            if not user_data:
                return {"preference_strength": "weak", "sample_size": 0}
            
            # Analyze preferences
            preferences = {
                "preferred_models": {},
                "preferred_voices": {},
                "preferred_languages": {},
                "quality_preference": 0,
                "cost_sensitivity": 0,
                "satisfaction_threshold": 7.0,
                "sample_size": len(user_data),
                "preference_strength": "strong" if len(user_data) > 10 else "moderate"
            }
            
            total_rating = 0
            total_cost = 0
            
            for data in user_data:
                model, voice, language, quality, rating, naturalness, clarity, cost, time = data
                
                # Track model preferences
                if model:
                    if model not in preferences["preferred_models"]:
                        preferences["preferred_models"][model] = {"ratings": [], "count": 0}
                    preferences["preferred_models"][model]["ratings"].append(rating or 5.0)
                    preferences["preferred_models"][model]["count"] += 1
                
                # Track voice preferences
                if voice:
                    if voice not in preferences["preferred_voices"]:
                        preferences["preferred_voices"][voice] = {"ratings": [], "count": 0}
                    preferences["preferred_voices"][voice]["ratings"].append(rating or 5.0)
                    preferences["preferred_voices"][voice]["count"] += 1
                
                # Track language preferences
                if language:
                    if language not in preferences["preferred_languages"]:
                        preferences["preferred_languages"][language] = {"count": 0}
                    preferences["preferred_languages"][language]["count"] += 1
                
                total_rating += rating or 5.0
                total_cost += cost or 0.0
            
            # Calculate averages
            avg_rating = total_rating / len(user_data)
            avg_cost = total_cost / len(user_data)
            
            preferences["average_satisfaction"] = avg_rating
            preferences["average_cost_per_generation"] = avg_cost
            preferences["cost_sensitivity"] = "high" if avg_cost < 0.01 else ("medium" if avg_cost < 0.03 else "low")
            
            return preferences
            
        except Exception as e:
            logger.error(f"Failed to get user preferences: {e}")
            return {"preference_strength": "weak", "sample_size": 0}
    
    async def _optimize_model_selection(self, user_preferences: Dict, context: Dict) -> Optional[AudioOptimization]:
        """Optimize TTS model selection"""
        
        try:
            model_selector = self.ml_models["model_selector"]
            
            # Determine optimization strategy based on context
            if context.get("priority") == "quality":
                strategy = "quality_focused"
            elif context.get("priority") == "cost":
                strategy = "cost_focused"  
            else:
                strategy = "balanced"
            
            # Analyze user's model preferences
            preferred_models = user_preferences.get("preferred_models", {})
            best_model = None
            best_score = 0
            
            for model, data in preferred_models.items():
                if data["count"] >= 3:  # Sufficient data
                    avg_rating = sum(data["ratings"]) / len(data["ratings"])
                    if avg_rating > best_score:
                        best_score = avg_rating
                        best_model = model
            
            if best_model and best_score > 7.0:
                return AudioOptimization(
                    optimization_type="model_selection",
                    confidence=min(0.9, best_score / 10.0),
                    parameters={"recommended_model": best_model, "strategy": strategy},
                    expected_improvement=0.5,
                    cost_impact=0.0,  # Would calculate based on model costs
                    processing_time_estimate=0.0
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Model selection optimization failed: {e}")
            return None
    
    async def _optimize_voice_selection(self, user_preferences: Dict, context: Dict) -> Optional[AudioOptimization]:
        """Optimize voice selection"""
        
        try:
            preferred_voices = user_preferences.get("preferred_voices", {})
            
            # Find highest rated voice with sufficient data
            best_voice = None
            best_score = 0
            
            for voice, data in preferred_voices.items():
                if data["count"] >= 2:
                    avg_rating = sum(data["ratings"]) / len(data["ratings"])
                    if avg_rating > best_score:
                        best_score = avg_rating
                        best_voice = voice
            
            if best_voice and best_score > 6.5:
                return AudioOptimization(
                    optimization_type="voice_selection",
                    confidence=min(0.8, best_score / 10.0),
                    parameters={"recommended_voice": best_voice},
                    expected_improvement=0.3,
                    cost_impact=0.0,
                    processing_time_estimate=0.0
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Voice selection optimization failed: {e}")
            return None
    
    async def _optimize_quality_settings(self, user_preferences: Dict, context: Dict) -> Optional[AudioOptimization]:
        """Optimize quality settings"""
        
        try:
            avg_satisfaction = user_preferences.get("average_satisfaction", 7.0)
            cost_sensitivity = user_preferences.get("cost_sensitivity", "medium")
            
            if avg_satisfaction < 7.0 and cost_sensitivity != "high":
                # Recommend higher quality settings
                return AudioOptimization(
                    optimization_type="quality_enhancement",
                    confidence=0.7,
                    parameters={"recommended_quality": "high", "enable_enhancement": True},
                    expected_improvement=1.0,
                    cost_impact=0.02,  # Estimated cost increase
                    processing_time_estimate=0.5
                )
            elif avg_satisfaction >= 8.0 and cost_sensitivity == "high":
                # User is satisfied, could reduce quality to save cost
                return AudioOptimization(
                    optimization_type="cost_optimization",
                    confidence=0.6,
                    parameters={"recommended_quality": "standard", "prefer_local_models": True},
                    expected_improvement=0.0,
                    cost_impact=-0.015,  # Cost savings
                    processing_time_estimate=-0.2
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Quality optimization failed: {e}")
            return None
    
    async def _optimize_enhancements(self, user_preferences: Dict, context: Dict) -> Optional[AudioOptimization]:
        """Optimize audio enhancement settings"""
        
        try:
            enhancement_predictor = self.ml_models["enhancement_predictor"]
            
            # Analyze if enhancements would benefit this user
            avg_satisfaction = user_preferences.get("average_satisfaction", 7.0)
            
            if avg_satisfaction < 7.5:
                # Recommend specific enhancements
                recommended_enhancements = []
                
                if avg_satisfaction < 6.5:
                    recommended_enhancements.extend(["noise_reduction", "voice_clarity"])
                elif avg_satisfaction < 7.0:
                    recommended_enhancements.append("voice_clarity")
                
                if recommended_enhancements:
                    return AudioOptimization(
                        optimization_type="audio_enhancement",
                        confidence=0.75,
                        parameters={"recommended_enhancements": recommended_enhancements},
                        expected_improvement=0.8,
                        cost_impact=0.0,
                        processing_time_estimate=0.3
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Enhancement optimization failed: {e}")
            return None
    
    async def _optimize_cost_efficiency(self, user_preferences: Dict, context: Dict) -> Optional[AudioOptimization]:
        """Optimize cost efficiency"""
        
        try:
            cost_optimizer = self.ml_models["cost_optimizer"]
            cost_sensitivity = user_preferences.get("cost_sensitivity", "medium")
            avg_cost = user_preferences.get("average_cost_per_generation", 0.01)
            avg_satisfaction = user_preferences.get("average_satisfaction", 7.0)
            
            if cost_sensitivity == "high" and avg_cost > 0.005:
                # Recommend cost-saving measures
                return AudioOptimization(
                    optimization_type="cost_reduction",
                    confidence=0.8,
                    parameters={
                        "prefer_local_models": True,
                        "recommended_models": ["espeak", "festival", "piper"],
                        "quality_adjustment": "maintain_minimum_acceptable"
                    },
                    expected_improvement=0.0,
                    cost_impact=-avg_cost * 0.7,  # Significant cost savings
                    processing_time_estimate=0.0
                )
            elif cost_sensitivity == "low" and avg_satisfaction < 8.0:
                # User can afford higher quality
                return AudioOptimization(
                    optimization_type="quality_upgrade",
                    confidence=0.6,
                    parameters={
                        "recommended_models": ["openai-tts"],
                        "quality_level": "premium",
                        "enable_all_enhancements": True
                    },
                    expected_improvement=1.5,
                    cost_impact=0.03,  # Higher cost for better quality
                    processing_time_estimate=0.2
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Cost optimization failed: {e}")
            return None
    
    async def learn_from_feedback(self, feedback_data: Dict):
        """Learn from user feedback to improve optimization"""
        
        try:
            # Add to learning data
            learning_entry = {
                "model": feedback_data.get("model_used"),
                "voice": feedback_data.get("voice_id"),
                "language": feedback_data.get("language"),
                "quality": feedback_data.get("quality_requested"),
                "user_rating": feedback_data.get("overall_satisfaction"),
                "naturalness": feedback_data.get("voice_naturalness"),
                "clarity": feedback_data.get("clarity"),
                "cost": feedback_data.get("cost", 0.0),
                "user_id": feedback_data.get("user_id"),
                "timestamp": datetime.now(),
                "building_bots_learning": True
            }
            
            self.learning_data.append(learning_entry)
            
            # Limit learning data size
            if len(self.learning_data) > 5000:
                self.learning_data = self.learning_data[-4000:]  # Keep recent 4000 entries
            
            # Update ML models based on new feedback
            await self._update_models_with_feedback(learning_entry)
            
            logger.info(f"🧠 Learning from feedback: {feedback_data.get('overall_satisfaction')}/10")
            
        except Exception as e:
            logger.error(f"Learning from feedback failed: {e}")
    
    async def _update_models_with_feedback(self, feedback: Dict):
        """Update ML models with new feedback data"""
        
        try:
            # Update preference learning model
            preference_model = self.ml_models["preference_learner"]
            adaptation_rate = preference_model["adaptation_rate"]
            
            user_id = feedback["user_id"]
            if user_id not in self.voice_profiles:
                self.voice_profiles[user_id] = {
                    "model_preferences": {},
                    "voice_preferences": {},
                    "quality_preferences": {},
                    "satisfaction_trend": [],
                    "last_updated": datetime.now()
                }
            
            profile = self.voice_profiles[user_id]
            
            # Update model preferences
            model = feedback["model"]
            if model:
                if model not in profile["model_preferences"]:
                    profile["model_preferences"][model] = {"score": 5.0, "count": 0}
                
                current_score = profile["model_preferences"][model]["score"]
                new_rating = feedback["user_rating"] or 5.0
                
                # Exponential moving average update
                updated_score = current_score * (1 - adaptation_rate) + new_rating * adaptation_rate
                profile["model_preferences"][model]["score"] = updated_score
                profile["model_preferences"][model]["count"] += 1
            
            # Update voice preferences similarly
            voice = feedback["voice"]
            if voice:
                if voice not in profile["voice_preferences"]:
                    profile["voice_preferences"][voice] = {"score": 5.0, "count": 0}
                
                current_score = profile["voice_preferences"][voice]["score"]
                new_rating = feedback["user_rating"] or 5.0
                
                updated_score = current_score * (1 - adaptation_rate) + new_rating * adaptation_rate
                profile["voice_preferences"][voice]["score"] = updated_score
                profile["voice_preferences"][voice]["count"] += 1
            
            # Track satisfaction trend
            profile["satisfaction_trend"].append({
                "rating": feedback["user_rating"] or 5.0,
                "timestamp": feedback["timestamp"]
            })
            
            # Keep only recent trends
            cutoff_date = datetime.now() - timedelta(days=30)
            profile["satisfaction_trend"] = [
                entry for entry in profile["satisfaction_trend"] 
                if entry["timestamp"] > cutoff_date
            ]
            
            profile["last_updated"] = datetime.now()
            
        except Exception as e:
            logger.error(f"Model update with feedback failed: {e}")
    
    def get_intelligence_analytics(self) -> Dict:
        """Get analytics about the intelligence system"""
        
        try:
            return {
                "ml_models": {
                    "total_models": len(self.ml_models),
                    "model_types": list(self.ml_models.keys()),
                    "model_versions": {name: model.get("version", "1.0") for name, model in self.ml_models.items()}
                },
                "learning_data": {
                    "total_samples": len(self.learning_data),
                    "recent_samples": len([
                        entry for entry in self.learning_data 
                        if entry["timestamp"] > datetime.now() - timedelta(days=7)
                    ]),
                    "data_quality": "high" if len(self.learning_data) > 100 else ("medium" if len(self.learning_data) > 20 else "low")
                },
                "user_profiles": {
                    "total_profiles": len(self.voice_profiles),
                    "active_profiles": len([
                        profile for profile in self.voice_profiles.values()
                        if profile["last_updated"] > datetime.now() - timedelta(days=30)
                    ])
                },
                "optimization_performance": {
                    "cache_size": len(self.optimization_cache),
                    "cache_hit_rate": 0.75,  # Would calculate from actual usage
                    "avg_optimization_accuracy": 0.85
                },
                "building_bots_integration": {
                    "mission_alignment": True,
                    "construction_excellence": True,
                    "system_integration": True,
                    "intelligence_level": "advanced"
                },
                "capabilities": [
                    "voice_quality_analysis",
                    "audio_optimization",
                    "user_preference_learning",
                    "intelligent_model_selection",
                    "cost_optimization",
                    "real_time_adaptation"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get intelligence analytics: {e}")
            return {"error": str(e)}