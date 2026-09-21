"""
Mood Detection from Writing Patterns
Analyzes text to detect emotional states and mood patterns
"""

import asyncio
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import sqlite3
import nltk
from textblob import TextBlob
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import pickle
import hashlib

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/vader_lexicon')
except LookupError:
    nltk.download('vader_lexicon')

from nltk.sentiment import SentimentIntensityAnalyzer

logger = logging.getLogger(__name__)

class MoodState(Enum):
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"
    ANXIOUS = "anxious"
    EXCITED = "excited"
    CALM = "calm"
    STRESSED = "stressed"
    CONFUSED = "confused"
    CONFIDENT = "confident"
    MELANCHOLIC = "melancholic"

class EmotionalIntensity(Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"

@dataclass
class MoodDetectionConfig:
    """Configuration for mood detection"""
    confidence_threshold: float = 0.7
    temporal_window: int = 24  # hours
    min_text_length: int = 10  # minimum characters
    language_support: List[str] = field(default_factory=lambda: ['en'])
    enable_context_analysis: bool = True
    enable_pattern_learning: bool = True
    sentiment_weights: Dict[str, float] = field(default_factory=lambda: {
        'compound': 0.4,
        'pos': 0.25,
        'neu': 0.1,
        'neg': 0.25
    })

@dataclass
class WritingPatterns:
    """Analysis of writing patterns that indicate mood"""
    avg_sentence_length: float = 0.0
    punctuation_frequency: Dict[str, int] = field(default_factory=dict)
    capitalization_ratio: float = 0.0
    exclamation_count: int = 0
    question_count: int = 0
    repetition_patterns: List[str] = field(default_factory=list)
    word_diversity: float = 0.0
    typing_speed_indicator: float = 0.0
    emoji_count: int = 0
    emoji_sentiment: float = 0.0

@dataclass
class MoodAnalysis:
    """Result of mood analysis"""
    mood_state: MoodState
    confidence: float
    emotional_intensity: EmotionalIntensity
    sentiment_scores: Dict[str, float]
    writing_patterns: WritingPatterns
    contributing_factors: List[str]
    timestamp: datetime
    text_sample: str = ""
    user_id: str = ""
    context_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MoodTrend:
    """Mood trend over time"""
    user_id: str
    start_time: datetime
    end_time: datetime
    dominant_mood: MoodState
    mood_stability: float  # 0-1, higher = more stable
    mood_progression: List[Tuple[datetime, MoodState, float]]
    notable_events: List[Dict[str, Any]]
    pattern_insights: List[str]

class MoodDetector:
    """Main engine for mood detection from writing patterns"""
    
    def __init__(self, config: MoodDetectionConfig = None, db_path: str = None):
        self.config = config or MoodDetectionConfig()
        self.db_path = db_path or "mood_detection.db"
        
        # Initialize sentiment analyzer
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        
        # Initialize ML components
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.mood_classifier = None
        
        # Mood indicators and patterns
        self.mood_keywords = self._initialize_mood_keywords()
        self.writing_pattern_indicators = self._initialize_writing_patterns()
        
        # Initialize database
        self._init_database()
        
        # Load or train ML model
        asyncio.create_task(self._load_or_train_model())
        
        logger.info("Mood Detection Engine initialized")

    def _init_database(self):
        """Initialize SQLite database for mood data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mood_analyses (
                    analysis_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    mood_state TEXT,
                    confidence REAL,
                    emotional_intensity TEXT,
                    sentiment_scores TEXT,
                    writing_patterns TEXT,
                    contributing_factors TEXT,
                    timestamp TIMESTAMP,
                    text_sample TEXT,
                    context_data TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_writing_patterns (
                    user_id TEXT,
                    pattern_type TEXT,
                    pattern_data TEXT,
                    confidence REAL,
                    last_updated TIMESTAMP,
                    PRIMARY KEY (user_id, pattern_type)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mood_training_data (
                    text_id TEXT PRIMARY KEY,
                    text_content TEXT,
                    labeled_mood TEXT,
                    user_id TEXT,
                    timestamp TIMESTAMP,
                    verified BOOLEAN DEFAULT FALSE
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_mood_analyses_user_timestamp 
                ON mood_analyses (user_id, timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_patterns_updated 
                ON user_writing_patterns (user_id, last_updated)
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")

    def _initialize_mood_keywords(self) -> Dict[MoodState, List[str]]:
        """Initialize mood-specific keywords and phrases"""
        return {
            MoodState.VERY_POSITIVE: [
                'amazing', 'fantastic', 'incredible', 'wonderful', 'perfect', 'brilliant',
                'outstanding', 'marvelous', 'superb', 'excellent', 'thrilled', 'ecstatic',
                'overjoyed', 'elated', 'euphoric', 'blissful', 'delighted'
            ],
            MoodState.POSITIVE: [
                'good', 'great', 'nice', 'happy', 'pleased', 'glad', 'satisfied',
                'content', 'cheerful', 'upbeat', 'optimistic', 'hopeful', 'confident',
                'proud', 'grateful', 'thankful', 'blessed'
            ],
            MoodState.NEUTRAL: [
                'okay', 'fine', 'alright', 'normal', 'regular', 'usual', 'average',
                'standard', 'typical', 'ordinary', 'moderate'
            ],
            MoodState.NEGATIVE: [
                'bad', 'sad', 'unhappy', 'disappointed', 'frustrated', 'annoyed',
                'upset', 'down', 'low', 'discouraged', 'worried', 'concerned',
                'troubled', 'bothered', 'dissatisfied'
            ],
            MoodState.VERY_NEGATIVE: [
                'terrible', 'awful', 'horrible', 'devastating', 'crushing', 'heartbroken',
                'miserable', 'depressed', 'desperate', 'hopeless', 'devastated',
                'anguished', 'tormented', 'shattered', 'destroyed'
            ],
            MoodState.ANXIOUS: [
                'anxious', 'nervous', 'worried', 'stressed', 'tense', 'uneasy',
                'restless', 'agitated', 'panicked', 'fearful', 'apprehensive',
                'jittery', 'overwhelmed', 'frantic'
            ],
            MoodState.EXCITED: [
                'excited', 'thrilled', 'pumped', 'eager', 'enthusiastic', 'energetic',
                'animated', 'exhilarated', 'electrified', 'stimulated', 'fired up'
            ],
            MoodState.CALM: [
                'calm', 'peaceful', 'relaxed', 'serene', 'tranquil', 'composed',
                'collected', 'centered', 'balanced', 'steady', 'stable'
            ],
            MoodState.CONFUSED: [
                'confused', 'puzzled', 'perplexed', 'bewildered', 'lost', 'uncertain',
                'unclear', 'mixed up', 'baffled', 'mystified', 'disoriented'
            ],
            MoodState.CONFIDENT: [
                'confident', 'sure', 'certain', 'determined', 'assertive', 'bold',
                'strong', 'capable', 'competent', 'self-assured', 'empowered'
            ],
            MoodState.MELANCHOLIC: [
                'melancholic', 'wistful', 'nostalgic', 'pensive', 'reflective',
                'contemplative', 'somber', 'subdued', 'quiet', 'withdrawn'
            ]
        }

    def _initialize_writing_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize writing pattern indicators for different moods"""
        return {
            'sentence_length': {
                MoodState.EXCITED: {'min': 5, 'max': 15, 'indicator': 'short_burst'},
                MoodState.ANXIOUS: {'min': 20, 'max': 50, 'indicator': 'run_on'},
                MoodState.DEPRESSED: {'min': 3, 'max': 8, 'indicator': 'fragment'},
                MoodState.CALM: {'min': 12, 'max': 25, 'indicator': 'balanced'}
            },
            'punctuation': {
                'excessive_exclamation': {'mood': MoodState.EXCITED, 'threshold': 3},
                'excessive_question': {'mood': MoodState.CONFUSED, 'threshold': 2},
                'ellipsis_frequent': {'mood': MoodState.MELANCHOLIC, 'threshold': 2}
            },
            'capitalization': {
                'high_caps': {'mood': MoodState.STRESSED, 'threshold': 0.3},
                'all_caps_words': {'mood': MoodState.ANGRY, 'threshold': 2}
            },
            'repetition': {
                'word_repetition': {'mood': MoodState.ANXIOUS, 'threshold': 3},
                'phrase_repetition': {'mood': MoodState.STRESSED, 'threshold': 2}
            }
        }

    async def analyze_text_mood(self, text: str, user_id: str, 
                              context: Dict[str, Any] = None) -> MoodAnalysis:
        """Analyze text to detect mood and emotional state"""
        try:
            if len(text) < self.config.min_text_length:
                logger.warning(f"Text too short for mood analysis: {len(text)} characters")
                return None
            
            # Perform sentiment analysis
            sentiment_scores = self._analyze_sentiment(text)
            
            # Analyze writing patterns
            writing_patterns = await self._analyze_writing_patterns(text)
            
            # Detect mood using multiple approaches
            keyword_mood = await self._detect_mood_from_keywords(text)
            pattern_mood = await self._detect_mood_from_patterns(writing_patterns)
            
            # Use ML classifier if available
            ml_mood = None
            if self.mood_classifier:
                ml_mood = await self._classify_mood_ml(text)
            
            # Combine results to determine final mood
            final_mood, confidence = await self._combine_mood_predictions(
                sentiment_scores, keyword_mood, pattern_mood, ml_mood
            )
            
            # Determine emotional intensity
            intensity = self._calculate_emotional_intensity(sentiment_scores, writing_patterns)
            
            # Identify contributing factors
            contributing_factors = await self._identify_contributing_factors(
                text, sentiment_scores, writing_patterns, final_mood
            )
            
            # Create analysis result
            analysis = MoodAnalysis(
                mood_state=final_mood,
                confidence=confidence,
                emotional_intensity=intensity,
                sentiment_scores=sentiment_scores,
                writing_patterns=writing_patterns,
                contributing_factors=contributing_factors,
                timestamp=datetime.now(),
                text_sample=text[:200] + "..." if len(text) > 200 else text,
                user_id=user_id,
                context_data=context or {}
            )
            
            # Save to database
            await self._save_mood_analysis(analysis)
            
            # Update user patterns
            await self._update_user_patterns(user_id, writing_patterns, final_mood)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing text mood: {e}")
            return None

    def _analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Analyze sentiment using VADER sentiment analyzer"""
        try:
            # VADER sentiment analysis
            vader_scores = self.sentiment_analyzer.polarity_scores(text)
            
            # TextBlob sentiment analysis
            blob = TextBlob(text)
            textblob_polarity = blob.sentiment.polarity
            textblob_subjectivity = blob.sentiment.subjectivity
            
            # Combine scores
            combined_scores = {
                'vader_compound': vader_scores['compound'],
                'vader_positive': vader_scores['pos'],
                'vader_neutral': vader_scores['neu'],
                'vader_negative': vader_scores['neg'],
                'textblob_polarity': textblob_polarity,
                'textblob_subjectivity': textblob_subjectivity,
                'combined_sentiment': (vader_scores['compound'] + textblob_polarity) / 2
            }
            
            return combined_scores
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            return {'combined_sentiment': 0.0}

    async def _analyze_writing_patterns(self, text: str) -> WritingPatterns:
        """Analyze writing patterns that indicate mood"""
        try:
            # Split into sentences and words
            sentences = nltk.sent_tokenize(text)
            words = nltk.word_tokenize(text)
            
            # Calculate average sentence length
            avg_sentence_length = np.mean([len(nltk.word_tokenize(s)) for s in sentences]) if sentences else 0
            
            # Analyze punctuation
            punctuation_freq = {}
            for char in text:
                if char in '!?.,;:()[]{}"\'-':
                    punctuation_freq[char] = punctuation_freq.get(char, 0) + 1
            
            # Calculate capitalization ratio
            capital_letters = sum(1 for c in text if c.isupper())
            capitalization_ratio = capital_letters / len(text) if text else 0
            
            # Count specific punctuation
            exclamation_count = text.count('!')
            question_count = text.count('?')
            
            # Detect repetition patterns
            repetition_patterns = self._detect_repetitions(words)
            
            # Calculate word diversity
            unique_words = len(set(word.lower() for word in words if word.isalpha()))
            word_diversity = unique_words / len(words) if words else 0
            
            # Estimate typing speed indicators (based on text characteristics)
            typing_speed_indicator = self._estimate_typing_pattern(text)
            
            # Count and analyze emojis
            emoji_count = len(re.findall(r'[😀-🿿]', text))
            emoji_sentiment = self._analyze_emoji_sentiment(text)
            
            return WritingPatterns(
                avg_sentence_length=avg_sentence_length,
                punctuation_frequency=punctuation_freq,
                capitalization_ratio=capitalization_ratio,
                exclamation_count=exclamation_count,
                question_count=question_count,
                repetition_patterns=repetition_patterns,
                word_diversity=word_diversity,
                typing_speed_indicator=typing_speed_indicator,
                emoji_count=emoji_count,
                emoji_sentiment=emoji_sentiment
            )
            
        except Exception as e:
            logger.error(f"Error analyzing writing patterns: {e}")
            return WritingPatterns()

    def _detect_repetitions(self, words: List[str]) -> List[str]:
        """Detect repetitive patterns in text"""
        repetitions = []
        
        # Word repetitions
        word_counts = {}
        for word in words:
            if word.isalpha() and len(word) > 3:
                word_lower = word.lower()
                word_counts[word_lower] = word_counts.get(word_lower, 0) + 1
        
        for word, count in word_counts.items():
            if count >= 3:
                repetitions.append(f"word_repeat:{word}:{count}")
        
        # Character repetitions (like "nooooo")
        char_patterns = re.findall(r'(\w)\1{2,}', ' '.join(words))
        for pattern in char_patterns:
            repetitions.append(f"char_repeat:{pattern}")
        
        return repetitions

    def _estimate_typing_pattern(self, text: str) -> float:
        """Estimate typing patterns that might indicate mood"""
        # Simple heuristic based on text characteristics
        indicators = 0.0
        
        # Many typos or unusual spacing might indicate rushed/stressed typing
        if re.search(r'\s{2,}', text):  # Multiple spaces
            indicators += 0.2
        
        if re.search(r'[a-zA-Z]{15,}', text):  # Very long words (possible typos)
            indicators += 0.1
        
        # Frequent backtracking indicators
        if '...' in text:
            indicators += 0.1
        
        return min(indicators, 1.0)

    def _analyze_emoji_sentiment(self, text: str) -> float:
        """Analyze sentiment of emojis in text"""
        # Simplified emoji sentiment mapping
        positive_emojis = ['😀', '😁', '😂', '😃', '😄', '😅', '😊', '😋', '😎', '😍', '🥰', '😘', '🤗', '🤩', '🥳']
        negative_emojis = ['😢', '😭', '😰', '😨', '😱', '😞', '😔', '😟', '😕', '🙁', '☹️', '😣', '😖', '😫', '😤']
        
        positive_count = sum(1 for emoji in positive_emojis if emoji in text)
        negative_count = sum(1 for emoji in negative_emojis if emoji in text)
        
        total_emojis = positive_count + negative_count
        if total_emojis == 0:
            return 0.0
        
        return (positive_count - negative_count) / total_emojis

    async def _detect_mood_from_keywords(self, text: str) -> Tuple[MoodState, float]:
        """Detect mood based on keyword analysis"""
        text_lower = text.lower()
        mood_scores = {}
        
        for mood, keywords in self.mood_keywords.items():
            score = 0
            for keyword in keywords:
                # Count occurrences with word boundaries
                pattern = r'\b' + re.escape(keyword) + r'\b'
                matches = len(re.findall(pattern, text_lower))
                score += matches
            
            # Normalize by text length and keyword count
            normalized_score = score / (len(text.split()) * len(keywords))
            mood_scores[mood] = normalized_score
        
        # Find mood with highest score
        if not mood_scores or max(mood_scores.values()) == 0:
            return MoodState.NEUTRAL, 0.0
        
        best_mood = max(mood_scores, key=mood_scores.get)
        confidence = min(mood_scores[best_mood] * 10, 1.0)  # Scale and cap at 1.0
        
        return best_mood, confidence

    async def _detect_mood_from_patterns(self, patterns: WritingPatterns) -> Tuple[MoodState, float]:
        """Detect mood from writing patterns"""
        mood_indicators = []
        
        # Sentence length patterns
        if patterns.avg_sentence_length > 30:
            mood_indicators.append((MoodState.ANXIOUS, 0.6))
        elif patterns.avg_sentence_length < 5:
            mood_indicators.append((MoodState.VERY_NEGATIVE, 0.5))
        elif 5 <= patterns.avg_sentence_length <= 10:
            mood_indicators.append((MoodState.EXCITED, 0.4))
        
        # Punctuation patterns
        if patterns.exclamation_count >= 3:
            mood_indicators.append((MoodState.EXCITED, 0.7))
        elif patterns.question_count >= 2:
            mood_indicators.append((MoodState.CONFUSED, 0.6))
        
        # Capitalization patterns
        if patterns.capitalization_ratio > 0.2:
            mood_indicators.append((MoodState.STRESSED, 0.8))
        
        # Repetition patterns
        if any('word_repeat' in pattern for pattern in patterns.repetition_patterns):
            mood_indicators.append((MoodState.ANXIOUS, 0.6))
        
        # Emoji sentiment
        if patterns.emoji_sentiment > 0.5:
            mood_indicators.append((MoodState.POSITIVE, 0.6))
        elif patterns.emoji_sentiment < -0.5:
            mood_indicators.append((MoodState.NEGATIVE, 0.6))
        
        # Combine indicators
        if not mood_indicators:
            return MoodState.NEUTRAL, 0.0
        
        # Weight and combine mood indicators
        mood_weights = {}
        for mood, confidence in mood_indicators:
            mood_weights[mood] = mood_weights.get(mood, 0) + confidence
        
        best_mood = max(mood_weights, key=mood_weights.get)
        avg_confidence = mood_weights[best_mood] / len([m for m, c in mood_indicators if m == best_mood])
        
        return best_mood, min(avg_confidence, 1.0)

    async def _classify_mood_ml(self, text: str) -> Tuple[MoodState, float]:
        """Classify mood using ML model"""
        try:
            if not self.mood_classifier:
                return MoodState.NEUTRAL, 0.0
            
            # Vectorize text
            text_vector = self.vectorizer.transform([text])
            
            # Predict mood
            prediction = self.mood_classifier.predict(text_vector)[0]
            confidence = max(self.mood_classifier.predict_proba(text_vector)[0])
            
            return MoodState(prediction), confidence
            
        except Exception as e:
            logger.error(f"Error in ML mood classification: {e}")
            return MoodState.NEUTRAL, 0.0

    async def _combine_mood_predictions(self, sentiment_scores: Dict[str, float],
                                      keyword_result: Tuple[MoodState, float],
                                      pattern_result: Tuple[MoodState, float],
                                      ml_result: Optional[Tuple[MoodState, float]]) -> Tuple[MoodState, float]:
        """Combine different mood prediction approaches"""
        predictions = []
        
        # Add sentiment-based prediction
        sentiment = sentiment_scores.get('combined_sentiment', 0.0)
        if sentiment > 0.5:
            predictions.append((MoodState.POSITIVE, abs(sentiment) * 0.8))
        elif sentiment < -0.5:
            predictions.append((MoodState.NEGATIVE, abs(sentiment) * 0.8))
        else:
            predictions.append((MoodState.NEUTRAL, 0.5))
        
        # Add keyword prediction
        predictions.append(keyword_result)
        
        # Add pattern prediction
        predictions.append(pattern_result)
        
        # Add ML prediction if available
        if ml_result and ml_result[1] > 0.5:
            predictions.append(ml_result)
        
        # Weight and combine predictions
        mood_weights = {}
        total_weight = 0
        
        for mood, confidence in predictions:
            weight = confidence
            mood_weights[mood] = mood_weights.get(mood, 0) + weight
            total_weight += weight
        
        if total_weight == 0:
            return MoodState.NEUTRAL, 0.0
        
        # Normalize weights
        for mood in mood_weights:
            mood_weights[mood] /= total_weight
        
        best_mood = max(mood_weights, key=mood_weights.get)
        final_confidence = mood_weights[best_mood]
        
        return best_mood, final_confidence

    def _calculate_emotional_intensity(self, sentiment_scores: Dict[str, float], 
                                     patterns: WritingPatterns) -> EmotionalIntensity:
        """Calculate emotional intensity based on various factors"""
        intensity_score = 0.0
        
        # Sentiment intensity
        sentiment = abs(sentiment_scores.get('combined_sentiment', 0.0))
        intensity_score += sentiment * 0.4
        
        # Punctuation intensity
        if patterns.exclamation_count > 0:
            intensity_score += min(patterns.exclamation_count * 0.1, 0.3)
        
        # Capitalization intensity
        if patterns.capitalization_ratio > 0.1:
            intensity_score += min(patterns.capitalization_ratio * 0.5, 0.2)
        
        # Repetition intensity
        if patterns.repetition_patterns:
            intensity_score += min(len(patterns.repetition_patterns) * 0.05, 0.1)
        
        # Map score to intensity enum
        if intensity_score >= 0.8:
            return EmotionalIntensity.VERY_HIGH
        elif intensity_score >= 0.6:
            return EmotionalIntensity.HIGH
        elif intensity_score >= 0.4:
            return EmotionalIntensity.MODERATE
        elif intensity_score >= 0.2:
            return EmotionalIntensity.LOW
        else:
            return EmotionalIntensity.VERY_LOW

    async def _identify_contributing_factors(self, text: str, sentiment_scores: Dict[str, float],
                                           patterns: WritingPatterns, mood: MoodState) -> List[str]:
        """Identify factors that contributed to the mood detection"""
        factors = []
        
        # Sentiment factors
        sentiment = sentiment_scores.get('combined_sentiment', 0.0)
        if abs(sentiment) > 0.5:
            factors.append(f"Strong sentiment signal ({sentiment:.2f})")
        
        # Pattern factors
        if patterns.exclamation_count >= 2:
            factors.append(f"Frequent exclamations ({patterns.exclamation_count})")
        
        if patterns.capitalization_ratio > 0.15:
            factors.append(f"High capitalization ({patterns.capitalization_ratio:.2f})")
        
        if patterns.repetition_patterns:
            factors.append(f"Repetitive patterns ({len(patterns.repetition_patterns)})")
        
        if patterns.avg_sentence_length > 25:
            factors.append("Long sentences (possible anxiety)")
        elif patterns.avg_sentence_length < 8:
            factors.append("Short sentences (possible low mood)")
        
        # Emoji factors
        if patterns.emoji_count > 0:
            factors.append(f"Emoji usage ({patterns.emoji_count}, sentiment: {patterns.emoji_sentiment:.2f})")
        
        # Keyword factors
        text_lower = text.lower()
        for mood_state, keywords in self.mood_keywords.items():
            if mood_state == mood:
                found_keywords = [kw for kw in keywords if kw in text_lower]
                if found_keywords:
                    factors.append(f"Mood keywords: {', '.join(found_keywords[:3])}")
        
        return factors

    async def _save_mood_analysis(self, analysis: MoodAnalysis):
        """Save mood analysis to database"""
        try:
            analysis_id = hashlib.md5(
                f"{analysis.user_id}_{analysis.timestamp}_{analysis.text_sample[:50]}".encode()
            ).hexdigest()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO mood_analyses
                (analysis_id, user_id, mood_state, confidence, emotional_intensity,
                 sentiment_scores, writing_patterns, contributing_factors, timestamp,
                 text_sample, context_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                analysis_id,
                analysis.user_id,
                analysis.mood_state.value,
                analysis.confidence,
                analysis.emotional_intensity.value,
                json.dumps(analysis.sentiment_scores),
                json.dumps({
                    'avg_sentence_length': analysis.writing_patterns.avg_sentence_length,
                    'punctuation_frequency': analysis.writing_patterns.punctuation_frequency,
                    'capitalization_ratio': analysis.writing_patterns.capitalization_ratio,
                    'exclamation_count': analysis.writing_patterns.exclamation_count,
                    'question_count': analysis.writing_patterns.question_count,
                    'repetition_patterns': analysis.writing_patterns.repetition_patterns,
                    'word_diversity': analysis.writing_patterns.word_diversity,
                    'emoji_count': analysis.writing_patterns.emoji_count,
                    'emoji_sentiment': analysis.writing_patterns.emoji_sentiment
                }),
                json.dumps(analysis.contributing_factors),
                analysis.timestamp.isoformat(),
                analysis.text_sample,
                json.dumps(analysis.context_data)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving mood analysis: {e}")

    async def _update_user_patterns(self, user_id: str, patterns: WritingPatterns, mood: MoodState):
        """Update user-specific writing patterns"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            pattern_data = {
                'avg_sentence_length': patterns.avg_sentence_length,
                'capitalization_ratio': patterns.capitalization_ratio,
                'word_diversity': patterns.word_diversity,
                'emoji_sentiment': patterns.emoji_sentiment,
                'associated_mood': mood.value
            }
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_writing_patterns
                (user_id, pattern_type, pattern_data, confidence, last_updated)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id,
                'writing_style',
                json.dumps(pattern_data),
                0.8,  # Default confidence
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating user patterns: {e}")

    async def _load_or_train_model(self):
        """Load existing ML model or train a new one"""
        try:
            # Try to load existing model
            try:
                with open('mood_classifier.pkl', 'rb') as f:
                    model_data = pickle.load(f)
                    self.mood_classifier = model_data['classifier']
                    self.vectorizer = model_data['vectorizer']
                logger.info("Loaded existing mood classification model")
                return
            except FileNotFoundError:
                logger.info("No existing model found, will train new one")
            
            # If no model exists, train with sample data
            if self.config.enable_pattern_learning:
                await self._train_initial_model()
                
        except Exception as e:
            logger.error(f"Error loading/training model: {e}")

    async def _train_initial_model(self):
        """Train initial ML model with sample data"""
        try:
            # Sample training data (in a real implementation, this would be loaded from a larger dataset)
            training_data = [
                ("I'm so happy today! Everything is going great!", MoodState.POSITIVE.value),
                ("Feeling really excited about the new project!!! Can't wait to start!", MoodState.EXCITED.value),
                ("I'm worried about the meeting tomorrow. Not sure what to expect.", MoodState.ANXIOUS.value),
                ("Terrible day... everything went wrong", MoodState.VERY_NEGATIVE.value),
                ("Just a normal day, nothing special happening", MoodState.NEUTRAL.value),
                ("I feel so calm and peaceful right now", MoodState.CALM.value),
                ("This is confusing... I don't understand what's happening", MoodState.CONFUSED.value),
                ("I'm confident we can solve this problem", MoodState.CONFIDENT.value),
                ("Feeling a bit melancholic thinking about old times", MoodState.MELANCHOLIC.value),
                ("STRESSED OUT!!! Too much work to do!!!", MoodState.STRESSED.value)
            ]
            
            texts = [item[0] for item in training_data]
            labels = [item[1] for item in training_data]
            
            # Vectorize texts
            X = self.vectorizer.fit_transform(texts)
            y = labels
            
            # Train classifier
            self.mood_classifier = RandomForestClassifier(n_estimators=100, random_state=42)
            self.mood_classifier.fit(X, y)
            
            # Save model
            model_data = {
                'classifier': self.mood_classifier,
                'vectorizer': self.vectorizer
            }
            
            with open('mood_classifier.pkl', 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info("Trained initial mood classification model")
            
        except Exception as e:
            logger.error(f"Error training initial model: {e}")

    async def get_mood_trends(self, user_id: str, 
                            time_range: timedelta = timedelta(days=7)) -> MoodTrend:
        """Get mood trends for a user over time"""
        try:
            cutoff_time = datetime.now() - time_range
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT mood_state, confidence, timestamp, contributing_factors
                FROM mood_analyses
                WHERE user_id = ? AND timestamp > ?
                ORDER BY timestamp
            ''', (user_id, cutoff_time.isoformat()))
            
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                return MoodTrend(
                    user_id=user_id,
                    start_time=cutoff_time,
                    end_time=datetime.now(),
                    dominant_mood=MoodState.NEUTRAL,
                    mood_stability=0.0,
                    mood_progression=[],
                    notable_events=[],
                    pattern_insights=[]
                )
            
            # Analyze mood progression
            mood_progression = []
            mood_counts = {}
            
            for mood_str, confidence, timestamp_str, factors_str in rows:
                mood = MoodState(mood_str)
                timestamp = datetime.fromisoformat(timestamp_str)
                
                mood_progression.append((timestamp, mood, confidence))
                mood_counts[mood] = mood_counts.get(mood, 0) + 1
            
            # Find dominant mood
            dominant_mood = max(mood_counts, key=mood_counts.get)
            
            # Calculate stability (how consistent the mood has been)
            mood_changes = 0
            for i in range(1, len(mood_progression)):
                if mood_progression[i][1] != mood_progression[i-1][1]:
                    mood_changes += 1
            
            stability = max(0, 1 - (mood_changes / len(mood_progression))) if mood_progression else 0
            
            # Generate insights
            insights = self._generate_mood_insights(mood_progression, mood_counts)
            
            return MoodTrend(
                user_id=user_id,
                start_time=cutoff_time,
                end_time=datetime.now(),
                dominant_mood=dominant_mood,
                mood_stability=stability,
                mood_progression=mood_progression,
                notable_events=[],  # Would be populated with significant mood events
                pattern_insights=insights
            )
            
        except Exception as e:
            logger.error(f"Error getting mood trends: {e}")
            return MoodTrend(
                user_id=user_id,
                start_time=datetime.now() - time_range,
                end_time=datetime.now(),
                dominant_mood=MoodState.NEUTRAL,
                mood_stability=0.0,
                mood_progression=[],
                notable_events=[],
                pattern_insights=[]
            )

    def _generate_mood_insights(self, mood_progression: List[Tuple[datetime, MoodState, float]], 
                              mood_counts: Dict[MoodState, int]) -> List[str]:
        """Generate insights from mood patterns"""
        insights = []
        
        # Dominant mood insight
        if mood_counts:
            dominant_mood = max(mood_counts, key=mood_counts.get)
            percentage = (mood_counts[dominant_mood] / sum(mood_counts.values())) * 100
            insights.append(f"Dominant mood: {dominant_mood.value} ({percentage:.1f}% of the time)")
        
        # Mood diversity insight
        unique_moods = len(mood_counts)
        if unique_moods > 5:
            insights.append("High emotional variability - experiencing many different moods")
        elif unique_moods < 3:
            insights.append("Low emotional variability - relatively consistent mood state")
        
        # Positive vs negative balance
        positive_moods = [MoodState.VERY_POSITIVE, MoodState.POSITIVE, MoodState.EXCITED, MoodState.CONFIDENT]
        negative_moods = [MoodState.VERY_NEGATIVE, MoodState.NEGATIVE, MoodState.ANXIOUS, MoodState.STRESSED]
        
        positive_count = sum(mood_counts.get(mood, 0) for mood in positive_moods)
        negative_count = sum(mood_counts.get(mood, 0) for mood in negative_moods)
        
        if positive_count > negative_count * 2:
            insights.append("Generally positive emotional state")
        elif negative_count > positive_count * 2:
            insights.append("Experiencing more challenging emotions - consider support")
        
        return insights

    async def get_mood_statistics(self, user_id: str,
                                time_range: timedelta = timedelta(days=30)) -> Dict[str, Any]:
        """Get comprehensive mood statistics"""
        try:
            cutoff_time = datetime.now() - time_range
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get mood distribution
            cursor.execute('''
                SELECT mood_state, COUNT(*) as count, AVG(confidence) as avg_confidence
                FROM mood_analyses
                WHERE user_id = ? AND timestamp > ?
                GROUP BY mood_state
            ''', (user_id, cutoff_time.isoformat()))
            
            mood_distribution = {}
            for row in cursor.fetchall():
                mood_state, count, avg_confidence = row
                mood_distribution[mood_state] = {
                    'count': count,
                    'avg_confidence': avg_confidence
                }
            
            # Get emotional intensity distribution
            cursor.execute('''
                SELECT emotional_intensity, COUNT(*) as count
                FROM mood_analyses
                WHERE user_id = ? AND timestamp > ?
                GROUP BY emotional_intensity
            ''', (user_id, cutoff_time.isoformat()))
            
            intensity_distribution = {}
            for row in cursor.fetchall():
                intensity, count = row
                intensity_distribution[intensity] = count
            
            conn.close()
            
            # Calculate overall statistics
            total_analyses = sum(dist['count'] for dist in mood_distribution.values())
            avg_confidence = np.mean([dist['avg_confidence'] for dist in mood_distribution.values()]) if mood_distribution else 0
            
            return {
                'total_analyses': total_analyses,
                'mood_distribution': mood_distribution,
                'intensity_distribution': intensity_distribution,
                'average_confidence': avg_confidence,
                'time_range_days': time_range.days,
                'analysis_period': {
                    'start': cutoff_time.isoformat(),
                    'end': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting mood statistics: {e}")
            return {}

# CLI interface for testing
async def main():
    """CLI interface for testing mood detection"""
    print("Mood Detection Engine - Test Interface")
    print("=" * 50)
    
    # Initialize detector
    config = MoodDetectionConfig(
        confidence_threshold=0.6,
        enable_pattern_learning=True
    )
    
    detector = MoodDetector(config)
    
    # Wait a moment for model loading
    await asyncio.sleep(1)
    
    print("Available commands:")
    print("1. analyze <text> - Analyze mood in text")
    print("2. trends <user_id> - Show mood trends")
    print("3. stats <user_id> - Show mood statistics")
    print("4. config - Show current configuration")
    print("5. exit - Exit the program")
    
    while True:
        try:
            command = input("\nEnter command: ").strip()
            
            if command == "exit":
                break
            elif command.startswith("analyze "):
                text = command[8:]  # Remove "analyze " prefix
                print(f"Analyzing: '{text}'")
                
                analysis = await detector.analyze_text_mood(text, "test_user")
                if analysis:
                    print(f"\nMood Analysis Results:")
                    print(f"Mood State: {analysis.mood_state.value}")
                    print(f"Confidence: {analysis.confidence:.2f}")
                    print(f"Emotional Intensity: {analysis.emotional_intensity.value}")
                    print(f"Sentiment Score: {analysis.sentiment_scores.get('combined_sentiment', 0):.2f}")
                    print(f"Contributing Factors: {', '.join(analysis.contributing_factors)}")
                    print(f"Writing Patterns:")
                    print(f"  - Avg Sentence Length: {analysis.writing_patterns.avg_sentence_length:.1f}")
                    print(f"  - Exclamations: {analysis.writing_patterns.exclamation_count}")
                    print(f"  - Capitalization Ratio: {analysis.writing_patterns.capitalization_ratio:.2f}")
                    print(f"  - Emojis: {analysis.writing_patterns.emoji_count} (sentiment: {analysis.writing_patterns.emoji_sentiment:.2f})")
                else:
                    print("Failed to analyze mood")
                    
            elif command.startswith("trends "):
                user_id = command.split()[1]
                trends = await detector.get_mood_trends(user_id)
                print(f"\nMood Trends for {user_id}:")
                print(f"Dominant Mood: {trends.dominant_mood.value}")
                print(f"Mood Stability: {trends.mood_stability:.2f}")
                print(f"Pattern Insights: {', '.join(trends.pattern_insights)}")
                print(f"Recent Progression: {len(trends.mood_progression)} mood points")
                
            elif command.startswith("stats "):
                user_id = command.split()[1]
                stats = await detector.get_mood_statistics(user_id)
                print(f"\nMood Statistics for {user_id}:")
                print(json.dumps(stats, indent=2))
                
            elif command == "config":
                print("Current configuration:")
                print(f"Confidence threshold: {config.confidence_threshold}")
                print(f"Temporal window: {config.temporal_window} hours")
                print(f"Min text length: {config.min_text_length} characters")
                print(f"Enable pattern learning: {config.enable_pattern_learning}")
                
            else:
                print("Unknown command. Try 'analyze <text>', 'trends <user_id>', 'stats <user_id>', 'config', or 'exit'.")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
    
    print("Mood detection engine test completed.")

if __name__ == "__main__":
    asyncio.run(main())