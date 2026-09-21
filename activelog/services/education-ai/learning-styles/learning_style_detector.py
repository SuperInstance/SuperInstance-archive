"""
Learning Style Detection and Adaptation System

Advanced AI-powered system for detecting student learning styles and adapting
educational content delivery based on VARK model, behavioral analysis, and
performance correlation.
"""

import asyncio
import sqlite3
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LearningStyleType(Enum):
    VISUAL = "visual"
    AUDITORY = "auditory"
    READING_WRITING = "reading_writing"
    KINESTHETIC = "kinesthetic"

class ContentFormat(Enum):
    VIDEO = "video"
    AUDIO = "audio"
    TEXT = "text"
    INTERACTIVE = "interactive"
    DIAGRAM = "diagram"
    QUIZ = "quiz"
    SIMULATION = "simulation"
    DISCUSSION = "discussion"

@dataclass
class LearningStyleProfile:
    student_id: str
    visual_score: float = 0.0
    auditory_score: float = 0.0
    reading_writing_score: float = 0.0
    kinesthetic_score: float = 0.0
    dominant_style: Optional[LearningStyleType] = None
    confidence: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    assessment_data: Dict = field(default_factory=dict)
    behavioral_patterns: Dict = field(default_factory=dict)

@dataclass
class InteractionEvent:
    student_id: str
    event_type: str
    content_type: str
    duration: int
    engagement_score: float
    completion_rate: float
    timestamp: datetime
    metadata: Dict = field(default_factory=dict)

@dataclass
class ContentAdaptation:
    original_format: ContentFormat
    adapted_format: ContentFormat
    confidence: float
    reasoning: str
    effectiveness_prediction: float

class LearningStyleDetector:
    def __init__(self, db_path: str = "education_ai.db"):
        self.db_path = db_path
        self.ml_model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.init_database()
        
    def init_database(self):
        """Initialize database tables for learning style detection"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_style_profiles (
                student_id TEXT PRIMARY KEY,
                visual_score REAL,
                auditory_score REAL,
                reading_writing_score REAL,
                kinesthetic_score REAL,
                dominant_style TEXT,
                confidence REAL,
                last_updated TIMESTAMP,
                assessment_data TEXT,
                behavioral_patterns TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interaction_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT,
                event_type TEXT,
                content_type TEXT,
                duration INTEGER,
                engagement_score REAL,
                completion_rate REAL,
                timestamp TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (student_id) REFERENCES learning_style_profiles (student_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_adaptations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT,
                original_format TEXT,
                adapted_format TEXT,
                confidence REAL,
                reasoning TEXT,
                effectiveness_prediction REAL,
                actual_effectiveness REAL,
                timestamp TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES learning_style_profiles (student_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("Learning style detection database initialized")

    async def conduct_vark_assessment(self, student_id: str, responses: Dict[str, int]) -> LearningStyleProfile:
        """
        Conduct VARK learning style assessment
        
        Args:
            student_id: Student identifier
            responses: Assessment responses (16 questions, 4 options each)
            
        Returns:
            LearningStyleProfile with assessment results
        """
        visual_score = sum(responses.get(f"q{i}_visual", 0) for i in range(1, 17))
        auditory_score = sum(responses.get(f"q{i}_auditory", 0) for i in range(1, 17))
        reading_score = sum(responses.get(f"q{i}_reading", 0) for i in range(1, 17))
        kinesthetic_score = sum(responses.get(f"q{i}_kinesthetic", 0) for i in range(1, 17))
        
        total_score = visual_score + auditory_score + reading_score + kinesthetic_score
        
        if total_score == 0:
            logger.warning(f"No responses provided for student {student_id}")
            return LearningStyleProfile(student_id=student_id)
            
        visual_pct = visual_score / total_score
        auditory_pct = auditory_score / total_score
        reading_pct = reading_score / total_score
        kinesthetic_pct = kinesthetic_score / total_score
        
        style_scores = {
            LearningStyleType.VISUAL: visual_pct,
            LearningStyleType.AUDITORY: auditory_pct,
            LearningStyleType.READING_WRITING: reading_pct,
            LearningStyleType.KINESTHETIC: kinesthetic_pct
        }
        
        dominant_style = max(style_scores.keys(), key=lambda x: style_scores[x])
        confidence = style_scores[dominant_style]
        
        profile = LearningStyleProfile(
            student_id=student_id,
            visual_score=visual_pct,
            auditory_score=auditory_pct,
            reading_writing_score=reading_pct,
            kinesthetic_score=kinesthetic_pct,
            dominant_style=dominant_style,
            confidence=confidence,
            assessment_data=responses
        )
        
        await self._save_profile(profile)
        logger.info(f"VARK assessment completed for student {student_id}: {dominant_style.value} ({confidence:.2f})")
        
        return profile

    async def analyze_behavioral_patterns(self, student_id: str, days_back: int = 30) -> Dict[str, Any]:
        """
        Analyze student behavioral patterns to infer learning style
        
        Args:
            student_id: Student identifier
            days_back: Number of days to analyze
            
        Returns:
            Dictionary with behavioral analysis results
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        cursor.execute('''
            SELECT event_type, content_type, duration, engagement_score, completion_rate
            FROM interaction_events
            WHERE student_id = ? AND timestamp > ?
        ''', (student_id, cutoff_date))
        
        interactions = cursor.fetchall()
        conn.close()
        
        if not interactions:
            return {"error": "Insufficient interaction data"}
            
        patterns = {
            "content_preferences": {},
            "engagement_by_format": {},
            "completion_by_format": {},
            "time_patterns": {},
            "interaction_frequency": len(interactions)
        }
        
        for event_type, content_type, duration, engagement, completion in interactions:
            if content_type not in patterns["content_preferences"]:
                patterns["content_preferences"][content_type] = {"count": 0, "total_duration": 0}
            
            patterns["content_preferences"][content_type]["count"] += 1
            patterns["content_preferences"][content_type]["total_duration"] += duration
            
            if content_type not in patterns["engagement_by_format"]:
                patterns["engagement_by_format"][content_type] = []
            patterns["engagement_by_format"][content_type].append(engagement)
            
            if content_type not in patterns["completion_by_format"]:
                patterns["completion_by_format"][content_type] = []
            patterns["completion_by_format"][content_type].append(completion)
        
        for content_type in patterns["engagement_by_format"]:
            patterns["engagement_by_format"][content_type] = np.mean(patterns["engagement_by_format"][content_type])
            patterns["completion_by_format"][content_type] = np.mean(patterns["completion_by_format"][content_type])
        
        return patterns

    async def predict_learning_style(self, student_id: str) -> LearningStyleProfile:
        """
        Predict learning style using behavioral analysis and ML
        
        Args:
            student_id: Student identifier
            
        Returns:
            Predicted learning style profile
        """
        behavioral_data = await self.analyze_behavioral_patterns(student_id)
        
        if "error" in behavioral_data:
            logger.warning(f"Cannot predict learning style for {student_id}: {behavioral_data['error']}")
            return LearningStyleProfile(student_id=student_id)
        
        features = self._extract_features(behavioral_data)
        
        if not self.is_trained:
            await self._train_model()
        
        if self.is_trained:
            features_scaled = self.scaler.transform([features])
            style_probs = self.ml_model.predict_proba(features_scaled)[0]
            
            styles = [LearningStyleType.VISUAL, LearningStyleType.AUDITORY, 
                     LearningStyleType.READING_WRITING, LearningStyleType.KINESTHETIC]
            
            style_scores = dict(zip(styles, style_probs))
            dominant_style = max(style_scores.keys(), key=lambda x: style_scores[x])
            confidence = style_scores[dominant_style]
            
            profile = LearningStyleProfile(
                student_id=student_id,
                visual_score=style_scores[LearningStyleType.VISUAL],
                auditory_score=style_scores[LearningStyleType.AUDITORY],
                reading_writing_score=style_scores[LearningStyleType.READING_WRITING],
                kinesthetic_score=style_scores[LearningStyleType.KINESTHETIC],
                dominant_style=dominant_style,
                confidence=confidence,
                behavioral_patterns=behavioral_data
            )
        else:
            profile = self._heuristic_prediction(behavioral_data, student_id)
        
        await self._save_profile(profile)
        return profile

    def _extract_features(self, behavioral_data: Dict[str, Any]) -> List[float]:
        """Extract ML features from behavioral data"""
        features = []
        
        content_prefs = behavioral_data.get("content_preferences", {})
        engagement = behavioral_data.get("engagement_by_format", {})
        completion = behavioral_data.get("completion_by_format", {})
        
        visual_indicators = ["video", "diagram", "image", "chart"]
        auditory_indicators = ["audio", "podcast", "discussion", "lecture"]
        text_indicators = ["text", "reading", "document", "article"]
        kinesthetic_indicators = ["interactive", "simulation", "lab", "exercise"]
        
        visual_engagement = np.mean([engagement.get(fmt, 0) for fmt in visual_indicators])
        auditory_engagement = np.mean([engagement.get(fmt, 0) for fmt in auditory_indicators])
        text_engagement = np.mean([engagement.get(fmt, 0) for fmt in text_indicators])
        kinesthetic_engagement = np.mean([engagement.get(fmt, 0) for fmt in kinesthetic_indicators])
        
        visual_completion = np.mean([completion.get(fmt, 0) for fmt in visual_indicators])
        auditory_completion = np.mean([completion.get(fmt, 0) for fmt in auditory_indicators])
        text_completion = np.mean([completion.get(fmt, 0) for fmt in text_indicators])
        kinesthetic_completion = np.mean([completion.get(fmt, 0) for fmt in kinesthetic_indicators])
        
        visual_time = sum([content_prefs.get(fmt, {}).get("total_duration", 0) for fmt in visual_indicators])
        auditory_time = sum([content_prefs.get(fmt, {}).get("total_duration", 0) for fmt in auditory_indicators])
        text_time = sum([content_prefs.get(fmt, {}).get("total_duration", 0) for fmt in text_indicators])
        kinesthetic_time = sum([content_prefs.get(fmt, {}).get("total_duration", 0) for fmt in kinesthetic_indicators])
        
        total_time = visual_time + auditory_time + text_time + kinesthetic_time
        if total_time > 0:
            visual_time_pct = visual_time / total_time
            auditory_time_pct = auditory_time / total_time
            text_time_pct = text_time / total_time
            kinesthetic_time_pct = kinesthetic_time / total_time
        else:
            visual_time_pct = auditory_time_pct = text_time_pct = kinesthetic_time_pct = 0.25
        
        features = [
            visual_engagement, auditory_engagement, text_engagement, kinesthetic_engagement,
            visual_completion, auditory_completion, text_completion, kinesthetic_completion,
            visual_time_pct, auditory_time_pct, text_time_pct, kinesthetic_time_pct,
            behavioral_data.get("interaction_frequency", 0)
        ]
        
        return features

    def _heuristic_prediction(self, behavioral_data: Dict[str, Any], student_id: str) -> LearningStyleProfile:
        """Heuristic learning style prediction when ML model unavailable"""
        engagement = behavioral_data.get("engagement_by_format", {})
        completion = behavioral_data.get("completion_by_format", {})
        
        style_indicators = {
            LearningStyleType.VISUAL: ["video", "diagram", "image", "chart"],
            LearningStyleType.AUDITORY: ["audio", "podcast", "discussion", "lecture"],
            LearningStyleType.READING_WRITING: ["text", "reading", "document", "article"],
            LearningStyleType.KINESTHETIC: ["interactive", "simulation", "lab", "exercise"]
        }
        
        style_scores = {}
        for style, indicators in style_indicators.items():
            eng_score = np.mean([engagement.get(fmt, 0) for fmt in indicators])
            comp_score = np.mean([completion.get(fmt, 0) for fmt in indicators])
            style_scores[style] = (eng_score + comp_score) / 2
        
        if not any(style_scores.values()):
            style_scores = {style: 0.25 for style in style_indicators.keys()}
        
        total_score = sum(style_scores.values())
        if total_score > 0:
            style_scores = {k: v/total_score for k, v in style_scores.items()}
        
        dominant_style = max(style_scores.keys(), key=lambda x: style_scores[x])
        confidence = style_scores[dominant_style]
        
        return LearningStyleProfile(
            student_id=student_id,
            visual_score=style_scores[LearningStyleType.VISUAL],
            auditory_score=style_scores[LearningStyleType.AUDITORY],
            reading_writing_score=style_scores[LearningStyleType.READING_WRITING],
            kinesthetic_score=style_scores[LearningStyleType.KINESTHETIC],
            dominant_style=dominant_style,
            confidence=confidence,
            behavioral_patterns=behavioral_data
        )

    async def _train_model(self):
        """Train ML model using existing profile data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT student_id, visual_score, auditory_score, reading_writing_score, 
                   kinesthetic_score, dominant_style, behavioral_patterns
            FROM learning_style_profiles
            WHERE behavioral_patterns IS NOT NULL AND dominant_style IS NOT NULL
        ''')
        
        profiles = cursor.fetchall()
        conn.close()
        
        if len(profiles) < 10:
            logger.info("Insufficient training data for ML model")
            return
        
        X, y = [], []
        for profile in profiles:
            try:
                behavioral_data = json.loads(profile[6])
                features = self._extract_features(behavioral_data)
                X.append(features)
                y.append(profile[5])
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Error processing training data: {e}")
                continue
        
        if len(X) >= 10:
            X = self.scaler.fit_transform(X)
            self.ml_model.fit(X, y)
            self.is_trained = True
            logger.info(f"ML model trained with {len(X)} samples")

    async def adapt_content(self, student_id: str, content_items: List[Dict]) -> List[ContentAdaptation]:
        """
        Adapt content based on student's learning style
        
        Args:
            student_id: Student identifier
            content_items: List of content items to adapt
            
        Returns:
            List of content adaptations
        """
        profile = await self.get_profile(student_id)
        if not profile or not profile.dominant_style:
            logger.warning(f"No learning style profile found for student {student_id}")
            return []
        
        adaptations = []
        
        style_preferences = {
            LearningStyleType.VISUAL: [ContentFormat.VIDEO, ContentFormat.DIAGRAM],
            LearningStyleType.AUDITORY: [ContentFormat.AUDIO, ContentFormat.DISCUSSION],
            LearningStyleType.READING_WRITING: [ContentFormat.TEXT, ContentFormat.QUIZ],
            LearningStyleType.KINESTHETIC: [ContentFormat.INTERACTIVE, ContentFormat.SIMULATION]
        }
        
        preferred_formats = style_preferences[profile.dominant_style]
        
        for item in content_items:
            original_format = ContentFormat(item.get("format", "text"))
            
            if original_format not in preferred_formats:
                adapted_format = preferred_formats[0]
                reasoning = f"Adapted to {profile.dominant_style.value} learning style"
                effectiveness_pred = profile.confidence * 0.8
            else:
                adapted_format = original_format
                reasoning = "Already matches learning style preference"
                effectiveness_pred = profile.confidence * 0.9
            
            adaptation = ContentAdaptation(
                original_format=original_format,
                adapted_format=adapted_format,
                confidence=profile.confidence,
                reasoning=reasoning,
                effectiveness_prediction=effectiveness_pred
            )
            
            adaptations.append(adaptation)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO content_adaptations 
                (student_id, original_format, adapted_format, confidence, reasoning, 
                 effectiveness_prediction, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (student_id, original_format.value, adapted_format.value,
                  adaptation.confidence, adaptation.reasoning,
                  adaptation.effectiveness_prediction, datetime.now()))
            conn.commit()
            conn.close()
        
        logger.info(f"Generated {len(adaptations)} content adaptations for student {student_id}")
        return adaptations

    async def record_interaction(self, interaction: InteractionEvent):
        """Record student interaction for behavioral analysis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO interaction_events
            (student_id, event_type, content_type, duration, engagement_score,
             completion_rate, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (interaction.student_id, interaction.event_type, interaction.content_type,
              interaction.duration, interaction.engagement_score,
              interaction.completion_rate, interaction.timestamp,
              json.dumps(interaction.metadata)))
        
        conn.commit()
        conn.close()
        
        if len(await self._get_recent_interactions(interaction.student_id)) >= 20:
            await self.update_learning_style(interaction.student_id)

    async def _get_recent_interactions(self, student_id: str, limit: int = 50) -> List[InteractionEvent]:
        """Get recent interactions for a student"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT student_id, event_type, content_type, duration, engagement_score,
                   completion_rate, timestamp, metadata
            FROM interaction_events
            WHERE student_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (student_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        interactions = []
        for row in rows:
            metadata = json.loads(row[7]) if row[7] else {}
            interaction = InteractionEvent(
                student_id=row[0],
                event_type=row[1],
                content_type=row[2],
                duration=row[3],
                engagement_score=row[4],
                completion_rate=row[5],
                timestamp=datetime.fromisoformat(row[6]),
                metadata=metadata
            )
            interactions.append(interaction)
        
        return interactions

    async def update_learning_style(self, student_id: str):
        """Update learning style based on recent interactions"""
        new_profile = await self.predict_learning_style(student_id)
        logger.info(f"Updated learning style for student {student_id}: {new_profile.dominant_style.value}")

    async def get_profile(self, student_id: str) -> Optional[LearningStyleProfile]:
        """Get learning style profile for student"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT student_id, visual_score, auditory_score, reading_writing_score,
                   kinesthetic_score, dominant_style, confidence, last_updated,
                   assessment_data, behavioral_patterns
            FROM learning_style_profiles
            WHERE student_id = ?
        ''', (student_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        assessment_data = json.loads(row[8]) if row[8] else {}
        behavioral_patterns = json.loads(row[9]) if row[9] else {}
        
        return LearningStyleProfile(
            student_id=row[0],
            visual_score=row[1],
            auditory_score=row[2],
            reading_writing_score=row[3],
            kinesthetic_score=row[4],
            dominant_style=LearningStyleType(row[5]) if row[5] else None,
            confidence=row[6],
            last_updated=datetime.fromisoformat(row[7]),
            assessment_data=assessment_data,
            behavioral_patterns=behavioral_patterns
        )

    async def _save_profile(self, profile: LearningStyleProfile):
        """Save learning style profile to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO learning_style_profiles
            (student_id, visual_score, auditory_score, reading_writing_score,
             kinesthetic_score, dominant_style, confidence, last_updated,
             assessment_data, behavioral_patterns)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (profile.student_id, profile.visual_score, profile.auditory_score,
              profile.reading_writing_score, profile.kinesthetic_score,
              profile.dominant_style.value if profile.dominant_style else None,
              profile.confidence, profile.last_updated,
              json.dumps(profile.assessment_data),
              json.dumps(profile.behavioral_patterns)))
        
        conn.commit()
        conn.close()

async def demo_learning_style_detection():
    """Demonstrate learning style detection and adaptation"""
    detector = LearningStyleDetector()
    
    # Example VARK assessment responses
    vark_responses = {
        "q1_visual": 1, "q1_auditory": 0, "q1_reading": 0, "q1_kinesthetic": 1,
        "q2_visual": 1, "q2_auditory": 0, "q2_reading": 1, "q2_kinesthetic": 0,
        "q3_visual": 1, "q3_auditory": 1, "q3_reading": 0, "q3_kinesthetic": 0,
        "q4_visual": 0, "q4_auditory": 0, "q4_reading": 1, "q4_kinesthetic": 1,
        "q5_visual": 1, "q5_auditory": 0, "q5_reading": 0, "q5_kinesthetic": 0,
        "q6_visual": 0, "q6_auditory": 1, "q6_reading": 1, "q6_kinesthetic": 0,
        "q7_visual": 1, "q7_auditory": 0, "q7_reading": 0, "q7_kinesthetic": 1,
        "q8_visual": 1, "q8_auditory": 1, "q8_reading": 0, "q8_kinesthetic": 0,
    }
    
    print("=== Learning Style Detection Demo ===")
    
    # VARK Assessment
    profile = await detector.conduct_vark_assessment("student_sarah", vark_responses)
    print(f"\nSarah's Learning Style Profile:")
    print(f"Dominant Style: {profile.dominant_style.value} (confidence: {profile.confidence:.2f})")
    print(f"Visual: {profile.visual_score:.2f}, Auditory: {profile.auditory_score:.2f}")
    print(f"Reading/Writing: {profile.reading_writing_score:.2f}, Kinesthetic: {profile.kinesthetic_score:.2f}")
    
    # Simulate interaction events
    interactions = [
        InteractionEvent("student_sarah", "content_view", "video", 300, 0.85, 0.95, datetime.now()),
        InteractionEvent("student_sarah", "content_view", "diagram", 180, 0.90, 1.0, datetime.now()),
        InteractionEvent("student_sarah", "content_view", "text", 120, 0.60, 0.70, datetime.now()),
        InteractionEvent("student_sarah", "quiz_attempt", "interactive", 240, 0.75, 0.80, datetime.now()),
        InteractionEvent("student_sarah", "content_view", "video", 420, 0.88, 0.90, datetime.now()),
    ]
    
    for interaction in interactions:
        await detector.record_interaction(interaction)
    
    # Behavioral analysis
    behavioral_data = await detector.analyze_behavioral_patterns("student_sarah")
    print(f"\nBehavioral Analysis:")
    print(f"Content Preferences: {behavioral_data.get('content_preferences', {})}")
    print(f"Engagement by Format: {behavioral_data.get('engagement_by_format', {})}")
    
    # Content adaptation
    content_items = [
        {"id": "math_lesson_1", "format": "text", "topic": "algebra"},
        {"id": "history_lesson_1", "format": "audio", "topic": "world_war_2"},
        {"id": "science_lab_1", "format": "interactive", "topic": "chemistry"}
    ]
    
    adaptations = await detector.adapt_content("student_sarah", content_items)
    print(f"\nContent Adaptations:")
    for i, adaptation in enumerate(adaptations):
        print(f"Item {i+1}: {adaptation.original_format.value} → {adaptation.adapted_format.value}")
        print(f"  Reasoning: {adaptation.reasoning}")
        print(f"  Predicted Effectiveness: {adaptation.effectiveness_prediction:.2f}")

if __name__ == "__main__":
    asyncio.run(demo_learning_style_detection())