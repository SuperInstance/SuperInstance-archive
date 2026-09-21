"""
Sentiment Analysis System
"""

import re
import json
from typing import Dict, Any, List, Tuple
from datetime import datetime


class SentimentAnalyzer:
    def __init__(self):
        # Sentiment keywords and patterns
        self.positive_words = {
            "excellent", "great", "good", "wonderful", "amazing", "fantastic",
            "perfect", "love", "like", "happy", "satisfied", "pleased",
            "thank", "thanks", "appreciate", "helpful", "awesome", "brilliant"
        }
        
        self.negative_words = {
            "terrible", "awful", "bad", "horrible", "hate", "disappointed",
            "frustrated", "angry", "upset", "problem", "issue", "wrong",
            "error", "broken", "failed", "useless", "annoying", "stupid"
        }
        
        self.frustrated_indicators = {
            "frustrated", "annoying", "ridiculous", "unacceptable", "enough",
            "sick", "tired", "fed up", "waste", "stupid", "incompetent"
        }
        
        self.urgent_indicators = {
            "urgent", "emergency", "immediate", "asap", "quickly", "rush",
            "critical", "important", "deadline", "time sensitive", "hurry"
        }
        
        # Emotional patterns
        self.emotion_patterns = {
            "anger": ["angry", "mad", "furious", "outraged", "livid", "pissed"],
            "sadness": ["sad", "disappointed", "depressed", "unhappy", "hurt"],
            "joy": ["happy", "excited", "thrilled", "delighted", "cheerful"],
            "fear": ["worried", "scared", "anxious", "nervous", "concerned"],
            "surprise": ["surprised", "shocked", "amazed", "astonished"],
            "disgust": ["disgusted", "repulsed", "sick", "revolted"]
        }
        
        # Tone indicators
        self.formal_indicators = {
            "please", "would", "could", "may i", "excuse me", "pardon",
            "sir", "madam", "mr", "ms", "dr", "professor"
        }
        
        self.casual_indicators = {
            "hey", "hi", "yeah", "yep", "nope", "gonna", "wanna",
            "ok", "okay", "cool", "awesome", "dude", "guys"
        }
        
        self.aggressive_indicators = {
            "demand", "insist", "better", "immediately", "unacceptable",
            "ridiculous", "pathetic", "useless", "incompetent"
        }
    
    async def analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text input"""
        
        if not text or not text.strip():
            return self._create_neutral_result()
        
        text_lower = text.lower()
        
        # Basic sentiment scoring
        sentiment_score = self._calculate_sentiment_score(text_lower)
        sentiment_type = self._determine_sentiment_type(sentiment_score)
        
        # Detect emotions
        emotions = self._detect_emotions(text_lower)
        
        # Analyze tone
        tone = self._analyze_tone(text_lower)
        
        # Check for frustration and urgency
        frustration_level = self._detect_frustration(text_lower)
        urgency_level = self._detect_urgency(text_lower)
        
        # Calculate confidence
        confidence = self._calculate_confidence(text_lower, sentiment_score)
        
        return {
            "type": sentiment_type,
            "score": sentiment_score,
            "confidence": confidence,
            "emotions": emotions,
            "tone": tone,
            "frustration_level": frustration_level,
            "urgency_level": urgency_level,
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "text_features": {
                "length": len(text),
                "word_count": len(text.split()),
                "has_questions": "?" in text,
                "has_exclamations": "!" in text,
                "all_caps": text.isupper(),
                "repeated_chars": self._detect_repeated_chars(text)
            }
        }
    
    async def analyze_conversation_sentiment(
        self,
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze sentiment trajectory over a conversation"""
        
        if not messages:
            return {"overall_sentiment": "neutral", "trajectory": "stable"}
        
        sentiment_history = []
        for message in messages:
            if message.get("message_type") == "user":
                sentiment = await self.analyze_text(message.get("content", ""))
                sentiment_history.append({
                    "timestamp": message.get("timestamp"),
                    "sentiment": sentiment["type"],
                    "score": sentiment["score"],
                    "frustration": sentiment["frustration_level"]
                })
        
        if not sentiment_history:
            return {"overall_sentiment": "neutral", "trajectory": "stable"}
        
        # Calculate trajectory
        trajectory = self._calculate_sentiment_trajectory(sentiment_history)
        
        # Determine overall sentiment
        avg_score = sum(s["score"] for s in sentiment_history) / len(sentiment_history)
        overall_sentiment = self._determine_sentiment_type(avg_score)
        
        # Check for escalation pattern
        escalation_risk = self._assess_escalation_risk(sentiment_history)
        
        return {
            "overall_sentiment": overall_sentiment,
            "average_score": avg_score,
            "trajectory": trajectory,
            "escalation_risk": escalation_risk,
            "sentiment_changes": len(set(s["sentiment"] for s in sentiment_history)),
            "frustration_trend": self._calculate_frustration_trend(sentiment_history),
            "conversation_length": len(sentiment_history)
        }
    
    async def detect_emotional_triggers(
        self,
        text: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Detect specific emotional triggers in text"""
        
        text_lower = text.lower()
        triggers = {
            "wait_time": self._detect_wait_time_frustration(text_lower),
            "repetition": self._detect_repetition_frustration(text_lower),
            "misunderstanding": self._detect_misunderstanding(text_lower),
            "technical_issues": self._detect_technical_frustration(text_lower),
            "billing_concerns": self._detect_billing_frustration(text_lower),
            "service_quality": self._detect_service_frustration(text_lower)
        }
        
        # Filter active triggers
        active_triggers = {k: v for k, v in triggers.items() if v["detected"]}
        
        return {
            "triggers_detected": list(active_triggers.keys()),
            "trigger_details": active_triggers,
            "total_triggers": len(active_triggers),
            "severity": max([t["severity"] for t in active_triggers.values()], default=0)
        }
    
    async def suggest_response_tone(
        self,
        sentiment_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Suggest appropriate response tone based on sentiment"""
        
        sentiment_type = sentiment_analysis["type"]
        frustration_level = sentiment_analysis["frustration_level"]
        urgency_level = sentiment_analysis["urgency_level"]
        
        if sentiment_type == "frustrated" or frustration_level > 0.7:
            return {
                "tone": "empathetic_apologetic",
                "approach": "acknowledge_and_validate",
                "keywords": ["understand", "apologize", "help", "resolve"],
                "avoid": ["unfortunately", "however", "but", "policy"],
                "escalation_recommended": True
            }
        elif sentiment_type == "negative":
            return {
                "tone": "professional_helpful",
                "approach": "solution_focused",
                "keywords": ["help", "resolve", "solution", "assist"],
                "avoid": ["problem", "issue", "can't", "unable"],
                "escalation_recommended": False
            }
        elif urgency_level > 0.8:
            return {
                "tone": "responsive_efficient",
                "approach": "immediate_action",
                "keywords": ["immediately", "priority", "urgent", "right away"],
                "avoid": ["later", "eventually", "when possible"],
                "escalation_recommended": True
            }
        elif sentiment_type == "positive":
            return {
                "tone": "friendly_enthusiastic",
                "approach": "maintain_positivity",
                "keywords": ["great", "excellent", "happy", "glad"],
                "avoid": ["problem", "issue", "unfortunately"],
                "escalation_recommended": False
            }
        else:
            return {
                "tone": "professional_neutral",
                "approach": "informative_helpful",
                "keywords": ["assist", "help", "information", "support"],
                "avoid": [],
                "escalation_recommended": False
            }
    
    # Private methods
    def _calculate_sentiment_score(self, text: str) -> float:
        """Calculate numerical sentiment score (-1 to 1)"""
        
        words = text.split()
        positive_count = sum(1 for word in words if word in self.positive_words)
        negative_count = sum(1 for word in words if word in self.negative_words)
        
        # Apply weights based on intensity
        if any(word in text for word in ["love", "amazing", "excellent"]):
            positive_count += 1
        if any(word in text for word in ["hate", "terrible", "awful"]):
            negative_count += 1
        
        total_sentiment_words = positive_count + negative_count
        if total_sentiment_words == 0:
            return 0.0
        
        score = (positive_count - negative_count) / len(words)
        return max(-1.0, min(1.0, score * 3))  # Normalize and amplify
    
    def _determine_sentiment_type(self, score: float) -> str:
        """Determine sentiment category from score"""
        
        if score > 0.3:
            return "positive"
        elif score < -0.3:
            return "negative"
        elif score < -0.6:
            return "frustrated"
        else:
            return "neutral"
    
    def _detect_emotions(self, text: str) -> Dict[str, float]:
        """Detect emotional indicators in text"""
        
        emotions = {}
        words = text.split()
        
        for emotion, keywords in self.emotion_patterns.items():
            count = sum(1 for word in words if word in keywords)
            if count > 0:
                emotions[emotion] = min(1.0, count / len(words) * 10)
        
        return emotions
    
    def _analyze_tone(self, text: str) -> Dict[str, Any]:
        """Analyze communication tone"""
        
        formal_score = sum(1 for indicator in self.formal_indicators if indicator in text)
        casual_score = sum(1 for indicator in self.casual_indicators if indicator in text)
        aggressive_score = sum(1 for indicator in self.aggressive_indicators if indicator in text)
        
        # Determine primary tone
        if aggressive_score > 0:
            primary_tone = "aggressive"
        elif formal_score > casual_score:
            primary_tone = "formal"
        elif casual_score > 0:
            primary_tone = "casual"
        else:
            primary_tone = "neutral"
        
        return {
            "primary": primary_tone,
            "formality": formal_score / (formal_score + casual_score + 1),
            "aggression": aggressive_score,
            "politeness": formal_score > 0 and aggressive_score == 0
        }
    
    def _detect_frustration(self, text: str) -> float:
        """Detect frustration level (0-1)"""
        
        frustration_count = sum(1 for word in self.frustrated_indicators if word in text)
        
        # Additional frustration indicators
        if "!!" in text:
            frustration_count += 1
        if text.count("!") > 2:
            frustration_count += 1
        if any(word in text for word in ["again", "still", "yet", "always"]):
            frustration_count += 0.5
        
        return min(1.0, frustration_count / 3)
    
    def _detect_urgency(self, text: str) -> float:
        """Detect urgency level (0-1)"""
        
        urgency_count = sum(1 for word in self.urgent_indicators if word in text)
        
        # Additional urgency indicators
        if "asap" in text or "a.s.a.p" in text:
            urgency_count += 1
        if "today" in text or "now" in text:
            urgency_count += 0.5
        if text.count("!") > 0:
            urgency_count += 0.3
        
        return min(1.0, urgency_count / 2)
    
    def _calculate_confidence(self, text: str, sentiment_score: float) -> float:
        """Calculate confidence in sentiment analysis"""
        
        # More text generally means higher confidence
        length_factor = min(1.0, len(text) / 100)
        
        # Strong sentiment words increase confidence
        sentiment_word_count = sum(1 for word in text.split() 
                                 if word in self.positive_words or word in self.negative_words)
        sentiment_factor = min(1.0, sentiment_word_count / 3)
        
        # Extreme scores are more confident
        score_factor = abs(sentiment_score)
        
        return (length_factor + sentiment_factor + score_factor) / 3
    
    def _detect_repeated_chars(self, text: str) -> bool:
        """Detect repeated characters (emphasis)"""
        
        return bool(re.search(r'(.)\1{2,}', text))
    
    def _calculate_sentiment_trajectory(self, sentiment_history: List[Dict]) -> str:
        """Calculate sentiment trajectory over conversation"""
        
        if len(sentiment_history) < 2:
            return "stable"
        
        scores = [s["score"] for s in sentiment_history]
        
        # Calculate trend
        if scores[-1] > scores[0] + 0.3:
            return "improving"
        elif scores[-1] < scores[0] - 0.3:
            return "declining"
        else:
            return "stable"
    
    def _assess_escalation_risk(self, sentiment_history: List[Dict]) -> str:
        """Assess risk of conversation escalation"""
        
        if not sentiment_history:
            return "low"
        
        recent_frustration = sentiment_history[-1]["frustration"] if sentiment_history else 0
        avg_frustration = sum(s["frustration"] for s in sentiment_history) / len(sentiment_history)
        
        if recent_frustration > 0.8 or avg_frustration > 0.6:
            return "high"
        elif recent_frustration > 0.5 or avg_frustration > 0.4:
            return "medium"
        else:
            return "low"
    
    def _calculate_frustration_trend(self, sentiment_history: List[Dict]) -> str:
        """Calculate frustration trend"""
        
        if len(sentiment_history) < 2:
            return "stable"
        
        recent_frustration = sum(s["frustration"] for s in sentiment_history[-3:]) / min(3, len(sentiment_history))
        early_frustration = sum(s["frustration"] for s in sentiment_history[:3]) / min(3, len(sentiment_history))
        
        if recent_frustration > early_frustration + 0.2:
            return "increasing"
        elif recent_frustration < early_frustration - 0.2:
            return "decreasing"
        else:
            return "stable"
    
    def _create_neutral_result(self) -> Dict[str, Any]:
        """Create neutral sentiment result for empty input"""
        
        return {
            "type": "neutral",
            "score": 0.0,
            "confidence": 0.0,
            "emotions": {},
            "tone": {"primary": "neutral"},
            "frustration_level": 0.0,
            "urgency_level": 0.0,
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "text_features": {
                "length": 0,
                "word_count": 0,
                "has_questions": False,
                "has_exclamations": False,
                "all_caps": False,
                "repeated_chars": False
            }
        }
    
    # Trigger detection methods
    def _detect_wait_time_frustration(self, text: str) -> Dict[str, Any]:
        """Detect frustration with wait times"""
        
        wait_keywords = ["waiting", "hold", "long time", "forever", "minutes", "hours"]
        detected = any(keyword in text for keyword in wait_keywords)
        
        severity = 0.5
        if "forever" in text or "hours" in text:
            severity = 0.9
        elif "long time" in text:
            severity = 0.7
        
        return {"detected": detected, "severity": severity if detected else 0}
    
    def _detect_repetition_frustration(self, text: str) -> Dict[str, Any]:
        """Detect frustration with repetition"""
        
        repeat_keywords = ["again", "already told", "repeat", "multiple times", "keep asking"]
        detected = any(keyword in text for keyword in repeat_keywords)
        
        return {"detected": detected, "severity": 0.8 if detected else 0}
    
    def _detect_misunderstanding(self, text: str) -> Dict[str, Any]:
        """Detect misunderstanding frustration"""
        
        misunderstand_keywords = ["don't understand", "not listening", "not getting", "confused"]
        detected = any(keyword in text for keyword in misunderstand_keywords)
        
        return {"detected": detected, "severity": 0.6 if detected else 0}
    
    def _detect_technical_frustration(self, text: str) -> Dict[str, Any]:
        """Detect technical issue frustration"""
        
        tech_keywords = ["not working", "broken", "error", "bug", "crashed", "frozen"]
        detected = any(keyword in text for keyword in tech_keywords)
        
        return {"detected": detected, "severity": 0.7 if detected else 0}
    
    def _detect_billing_frustration(self, text: str) -> Dict[str, Any]:
        """Detect billing-related frustration"""
        
        billing_keywords = ["charged", "overcharged", "wrong amount", "refund", "billing error"]
        detected = any(keyword in text for keyword in billing_keywords)
        
        return {"detected": detected, "severity": 0.8 if detected else 0}
    
    def _detect_service_frustration(self, text: str) -> Dict[str, Any]:
        """Detect service quality frustration"""
        
        service_keywords = ["poor service", "terrible service", "unprofessional", "rude"]
        detected = any(keyword in text for keyword in service_keywords)
        
        return {"detected": detected, "severity": 0.9 if detected else 0}