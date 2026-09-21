"""
Feedback and Survey Service

Manages post-session surveys, feedback collection, and sentiment analysis
to gather player insights and improve future sessions.
"""

import asyncio
import json
import uuid
import statistics
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from dataclasses import dataclass
from enum import Enum

from ..models.base import BaseSessionModel
from ..models.session import SessionSchema
from ..models.content import Survey, SurveyQuestion, SurveyResponse, FeedbackReport
from ..config import FEEDBACK_CONFIG


class QuestionType(str, Enum):
    RATING = "rating"
    MULTIPLE_CHOICE = "multiple_choice"
    TEXT = "text"
    YES_NO = "yes_no"
    RANKING = "ranking"
    SLIDER = "slider"


class SentimentType(str, Enum):
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


@dataclass
class QuestionTemplate:
    id: str
    text: str
    question_type: QuestionType
    options: Optional[List[str]] = None
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    required: bool = True
    category: str = "general"


@dataclass
class SurveyTemplate:
    id: str
    name: str
    description: str
    questions: List[QuestionTemplate]
    estimated_minutes: int
    category: str


@dataclass
class ResponseAnalysis:
    question_id: str
    question_text: str
    response_count: int
    average_rating: Optional[float]
    response_distribution: Dict[str, int]
    sentiment_analysis: Optional[SentimentType]
    key_themes: List[str]
    satisfaction_score: float


@dataclass
class SessionFeedback:
    session_id: str
    generated_at: datetime
    response_count: int
    response_rate: float
    overall_satisfaction: float
    question_analyses: List[ResponseAnalysis]
    common_themes: List[Tuple[str, int]]  # theme, frequency
    improvement_suggestions: List[str]
    positive_highlights: List[str]
    concerns_raised: List[str]
    dm_feedback: Optional[Dict[str, Any]]
    recommendations: List[str]


class SurveyTemplateManager:
    """Manages survey templates for different session types"""
    
    def __init__(self):
        self.templates: Dict[str, SurveyTemplate] = {}
        self._initialize_default_templates()
    
    def _initialize_default_templates(self):
        """Initialize default survey templates"""
        
        # Standard post-session survey
        standard_questions = [
            QuestionTemplate(
                id="overall_satisfaction",
                text="How satisfied were you with today's session overall?",
                question_type=QuestionType.RATING,
                min_value=1,
                max_value=10,
                category="satisfaction"
            ),
            QuestionTemplate(
                id="pacing_rating",
                text="How would you rate the pacing of today's session?",
                question_type=QuestionType.RATING,
                min_value=1,
                max_value=5,
                category="gameplay"
            ),
            QuestionTemplate(
                id="character_development",
                text="Did you feel your character had meaningful development opportunities?",
                question_type=QuestionType.YES_NO,
                category="character"
            ),
            QuestionTemplate(
                id="engagement_level",
                text="How engaged did you feel throughout the session?",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=["Very engaged", "Mostly engaged", "Somewhat engaged", "Barely engaged", "Not engaged"],
                category="engagement"
            ),
            QuestionTemplate(
                id="best_moment",
                text="What was your favorite moment from today's session?",
                question_type=QuestionType.TEXT,
                required=False,
                category="highlights"
            ),
            QuestionTemplate(
                id="improvement_suggestions",
                text="What could be improved for future sessions?",
                question_type=QuestionType.TEXT,
                required=False,
                category="improvement"
            ),
            QuestionTemplate(
                id="story_clarity",
                text="How clear was the story progression in today's session?",
                question_type=QuestionType.SLIDER,
                min_value=0,
                max_value=100,
                category="story"
            ),
            QuestionTemplate(
                id="group_dynamics",
                text="How would you rate the group dynamics and teamwork?",
                question_type=QuestionType.RATING,
                min_value=1,
                max_value=10,
                category="social"
            ),
            QuestionTemplate(
                id="content_preference",
                text="Rank these content types by preference for future sessions:",
                question_type=QuestionType.RANKING,
                options=["Combat encounters", "Roleplay scenes", "Exploration/puzzles", "Story/plot advancement"],
                category="preferences"
            ),
            QuestionTemplate(
                id="return_likelihood",
                text="How likely are you to attend the next session?",
                question_type=QuestionType.MULTIPLE_CHOICE,
                options=["Definitely", "Very likely", "Somewhat likely", "Unlikely", "Cannot attend"],
                category="attendance"
            )
        ]
        
        self.templates["standard"] = SurveyTemplate(
            id="standard",
            name="Standard Post-Session Survey",
            description="Comprehensive feedback survey for regular D&D sessions",
            questions=standard_questions,
            estimated_minutes=5,
            category="post_session"
        )
        
        # Quick feedback survey
        quick_questions = [
            QuestionTemplate(
                id="session_rating",
                text="Rate today's session (1-5 stars)",
                question_type=QuestionType.RATING,
                min_value=1,
                max_value=5,
                category="satisfaction"
            ),
            QuestionTemplate(
                id="highlight_text",
                text="One thing that stood out (optional)",
                question_type=QuestionType.TEXT,
                required=False,
                category="highlights"
            ),
            QuestionTemplate(
                id="next_session",
                text="Looking forward to next session?",
                question_type=QuestionType.YES_NO,
                category="attendance"
            )
        ]
        
        self.templates["quick"] = SurveyTemplate(
            id="quick",
            name="Quick Session Feedback",
            description="Brief 2-minute feedback survey",
            questions=quick_questions,
            estimated_minutes=2,
            category="post_session"
        )
        
        # Campaign milestone survey
        milestone_questions = [
            QuestionTemplate(
                id="campaign_satisfaction",
                text="How satisfied are you with the campaign's progress?",
                question_type=QuestionType.RATING,
                min_value=1,
                max_value=10,
                category="campaign"
            ),
            QuestionTemplate(
                id="character_growth",
                text="How satisfied are you with your character's development?",
                question_type=QuestionType.RATING,
                min_value=1,
                max_value=10,
                category="character"
            ),
            QuestionTemplate(
                id="story_investment",
                text="How invested are you in the ongoing story?",
                question_type=QuestionType.RATING,
                min_value=1,
                max_value=10,
                category="story"
            ),
            QuestionTemplate(
                id="campaign_highlights",
                text="What have been your favorite moments in the campaign so far?",
                question_type=QuestionType.TEXT,
                category="highlights"
            ),
            QuestionTemplate(
                id="campaign_concerns",
                text="Are there any concerns about the campaign direction?",
                question_type=QuestionType.TEXT,
                required=False,
                category="improvement"
            )
        ]
        
        self.templates["milestone"] = SurveyTemplate(
            id="milestone",
            name="Campaign Milestone Survey",
            description="Comprehensive survey for major campaign milestones",
            questions=milestone_questions,
            estimated_minutes=8,
            category="milestone"
        )
    
    async def get_template(self, template_id: str) -> Optional[SurveyTemplate]:
        """Get a survey template by ID"""
        return self.templates.get(template_id)
    
    async def create_custom_template(self, template: SurveyTemplate) -> str:
        """Create a custom survey template"""
        if not template.id:
            template.id = str(uuid.uuid4())
        
        self.templates[template.id] = template
        return template.id
    
    async def list_templates(self, category: str = None) -> List[SurveyTemplate]:
        """List all templates, optionally filtered by category"""
        templates = list(self.templates.values())
        
        if category:
            templates = [t for t in templates if t.category == category]
        
        return templates


class SentimentAnalyzer:
    """Analyzes sentiment in text responses"""
    
    def __init__(self):
        # Simple keyword-based sentiment analysis
        self.positive_words = {
            "amazing", "awesome", "great", "excellent", "fantastic", "wonderful",
            "love", "loved", "enjoyed", "fun", "exciting", "brilliant", "perfect",
            "outstanding", "incredible", "superb", "delightful", "impressive",
            "satisfying", "engaging", "captivating", "thrilling", "epic"
        }
        
        self.negative_words = {
            "terrible", "awful", "bad", "horrible", "disappointing", "boring",
            "hate", "hated", "dislike", "frustrated", "annoying", "confusing",
            "slow", "rushed", "unclear", "unfair", "difficult", "problems",
            "issues", "concerns", "worried", "uncomfortable", "awkward"
        }
        
        self.neutral_words = {
            "okay", "fine", "average", "normal", "standard", "typical",
            "moderate", "reasonable", "acceptable", "decent"
        }
    
    async def analyze_sentiment(self, text: str) -> SentimentType:
        """Analyze sentiment of text"""
        if not text:
            return SentimentType.NEUTRAL
        
        words = text.lower().split()
        
        positive_count = sum(1 for word in words if word in self.positive_words)
        negative_count = sum(1 for word in words if word in self.negative_words)
        neutral_count = sum(1 for word in words if word in self.neutral_words)
        
        # Calculate sentiment score
        total_sentiment_words = positive_count + negative_count + neutral_count
        
        if total_sentiment_words == 0:
            return SentimentType.NEUTRAL
        
        positive_ratio = positive_count / total_sentiment_words
        negative_ratio = negative_count / total_sentiment_words
        
        if positive_ratio >= 0.6:
            return SentimentType.VERY_POSITIVE
        elif positive_ratio >= 0.3:
            return SentimentType.POSITIVE
        elif negative_ratio >= 0.6:
            return SentimentType.VERY_NEGATIVE
        elif negative_ratio >= 0.3:
            return SentimentType.NEGATIVE
        else:
            return SentimentType.NEUTRAL
    
    async def extract_themes(self, texts: List[str]) -> List[Tuple[str, int]]:
        """Extract common themes from multiple text responses"""
        if not texts:
            return []
        
        # Combine all texts
        combined_text = " ".join(texts).lower()
        
        # Common D&D themes and keywords
        theme_keywords = {
            "combat": ["combat", "fight", "battle", "attack", "weapon", "spell", "tactical"],
            "roleplay": ["roleplay", "character", "acting", "personality", "dialogue", "interaction"],
            "story": ["story", "plot", "narrative", "mystery", "quest", "adventure"],
            "teamwork": ["team", "group", "together", "cooperation", "collaborative", "unity"],
            "difficulty": ["difficult", "hard", "easy", "challenging", "tough", "simple"],
            "pacing": ["pacing", "pace", "slow", "fast", "rushed", "tempo", "timing"],
            "creativity": ["creative", "innovative", "unique", "original", "clever", "imaginative"],
            "immersion": ["immersion", "immersive", "atmosphere", "mood", "setting", "world"],
            "rules": ["rules", "mechanics", "system", "rulebook", "regulation", "guideline"],
            "fun": ["fun", "enjoyable", "entertaining", "amusing", "pleasant", "delightful"]
        }
        
        theme_scores = {}
        
        for theme, keywords in theme_keywords.items():
            score = sum(combined_text.count(keyword) for keyword in keywords)
            if score > 0:
                theme_scores[theme] = score
        
        # Sort by frequency
        sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)
        
        return sorted_themes[:5]  # Top 5 themes


class ResponseAnalyzer:
    """Analyzes survey responses and generates insights"""
    
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
    
    async def analyze_question_responses(self, question: QuestionTemplate,
                                       responses: List[SurveyResponse]) -> ResponseAnalysis:
        """Analyze responses for a specific question"""
        
        response_count = len(responses)
        if response_count == 0:
            return self._empty_analysis(question)
        
        # Get response values
        response_values = [resp.response_value for resp in responses if resp.response_value]
        text_responses = [resp.response_text for resp in responses if resp.response_text]
        
        # Calculate average rating for numeric questions
        average_rating = None
        if question.question_type in [QuestionType.RATING, QuestionType.SLIDER]:
            numeric_values = []
            for value in response_values:
                try:
                    numeric_values.append(float(value))
                except (ValueError, TypeError):
                    pass
            
            if numeric_values:
                average_rating = statistics.mean(numeric_values)
        
        # Calculate response distribution
        response_distribution = {}
        if question.question_type in [QuestionType.MULTIPLE_CHOICE, QuestionType.YES_NO]:
            response_distribution = dict(Counter(response_values))
        elif question.question_type == QuestionType.RATING:
            response_distribution = dict(Counter(response_values))
        
        # Sentiment analysis for text responses
        sentiment_analysis = None
        if text_responses:
            all_text = " ".join(text_responses)
            sentiment_analysis = await self.sentiment_analyzer.analyze_sentiment(all_text)
        
        # Extract key themes from text responses
        key_themes = []
        if text_responses:
            themes = await self.sentiment_analyzer.extract_themes(text_responses)
            key_themes = [theme[0] for theme in themes[:3]]  # Top 3 themes
        
        # Calculate satisfaction score
        satisfaction_score = await self._calculate_satisfaction_score(
            question, response_values, average_rating, sentiment_analysis
        )
        
        return ResponseAnalysis(
            question_id=question.id,
            question_text=question.text,
            response_count=response_count,
            average_rating=average_rating,
            response_distribution=response_distribution,
            sentiment_analysis=sentiment_analysis,
            key_themes=key_themes,
            satisfaction_score=satisfaction_score
        )
    
    def _empty_analysis(self, question: QuestionTemplate) -> ResponseAnalysis:
        """Create empty analysis for questions with no responses"""
        return ResponseAnalysis(
            question_id=question.id,
            question_text=question.text,
            response_count=0,
            average_rating=None,
            response_distribution={},
            sentiment_analysis=None,
            key_themes=[],
            satisfaction_score=0.0
        )
    
    async def _calculate_satisfaction_score(self, question: QuestionTemplate,
                                          response_values: List[str],
                                          average_rating: Optional[float],
                                          sentiment_analysis: Optional[SentimentType]) -> float:
        """Calculate a satisfaction score (0-1) for the question responses"""
        
        if question.question_type in [QuestionType.RATING, QuestionType.SLIDER]:
            if average_rating is not None:
                max_value = question.max_value or 10
                return average_rating / max_value
        
        elif question.question_type == QuestionType.YES_NO:
            if response_values:
                yes_count = sum(1 for val in response_values if val.lower() in ["yes", "true", "1"])
                return yes_count / len(response_values)
        
        elif question.question_type == QuestionType.MULTIPLE_CHOICE:
            # Assume higher satisfaction for positive options
            positive_options = ["very engaged", "definitely", "very likely", "excellent"]
            if response_values:
                positive_count = sum(
                    1 for val in response_values 
                    if any(pos_opt in val.lower() for pos_opt in positive_options)
                )
                return positive_count / len(response_values)
        
        elif question.question_type == QuestionType.TEXT:
            if sentiment_analysis:
                sentiment_scores = {
                    SentimentType.VERY_POSITIVE: 1.0,
                    SentimentType.POSITIVE: 0.8,
                    SentimentType.NEUTRAL: 0.5,
                    SentimentType.NEGATIVE: 0.2,
                    SentimentType.VERY_NEGATIVE: 0.0
                }
                return sentiment_scores.get(sentiment_analysis, 0.5)
        
        return 0.5  # Default neutral satisfaction


class FeedbackService:
    """Main feedback and survey service"""
    
    def __init__(self):
        self.template_manager = SurveyTemplateManager()
        self.response_analyzer = ResponseAnalyzer()
        self.active_surveys: Dict[str, Survey] = {}
        self.survey_responses: Dict[str, List[SurveyResponse]] = defaultdict(list)
        self.session_feedback: Dict[str, SessionFeedback] = {}
    
    async def create_survey(self, session_id: str, template_id: str,
                           created_by: str, custom_questions: List[QuestionTemplate] = None,
                           expires_hours: int = 72) -> Optional[str]:
        """Create a new survey for a session"""
        
        template = await self.template_manager.get_template(template_id)
        if not template:
            return None
        
        # Use template questions or custom questions
        questions = custom_questions or template.questions
        
        survey = Survey(
            id=str(uuid.uuid4()),
            session_id=session_id,
            title=f"{template.name} - Session {session_id}",
            description=template.description,
            questions=questions,
            created_by=created_by,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
            is_active=True,
            estimated_minutes=template.estimated_minutes
        )
        
        self.active_surveys[survey.id] = survey
        return survey.id
    
    async def submit_survey_response(self, survey_id: str, participant_id: str,
                                   responses: List[Dict[str, Any]]) -> bool:
        """Submit survey responses from a participant"""
        
        survey = self.active_surveys.get(survey_id)
        if not survey or not survey.is_active:
            return False
        
        if datetime.utcnow() > survey.expires_at:
            return False
        
        # Check if participant already responded
        existing_responses = self.survey_responses.get(survey_id, [])
        if any(resp.participant_id == participant_id for resp in existing_responses):
            return False  # Already responded
        
        # Create response objects
        survey_responses = []
        for response_data in responses:
            question_id = response_data.get("question_id")
            
            # Find the question
            question = next((q for q in survey.questions if q.id == question_id), None)
            if not question:
                continue
            
            response = SurveyResponse(
                id=str(uuid.uuid4()),
                survey_id=survey_id,
                question_id=question_id,
                participant_id=participant_id,
                response_value=response_data.get("response_value"),
                response_text=response_data.get("response_text"),
                submitted_at=datetime.utcnow()
            )
            
            survey_responses.append(response)
        
        # Store responses
        self.survey_responses[survey_id].extend(survey_responses)
        
        return True
    
    async def generate_session_feedback(self, survey_id: str) -> Optional[SessionFeedback]:
        """Generate comprehensive feedback analysis for a session"""
        
        survey = self.active_surveys.get(survey_id)
        if not survey:
            return None
        
        responses = self.survey_responses.get(survey_id, [])
        
        # Get unique participants
        participants = set(resp.participant_id for resp in responses)
        response_count = len(participants)
        
        # Calculate response rate (assuming we know expected participants)
        # This would typically come from the session data
        expected_participants = 5  # Placeholder - should come from session data
        response_rate = (response_count / expected_participants) * 100 if expected_participants > 0 else 0
        
        # Analyze each question
        question_analyses = []
        overall_ratings = []
        
        for question in survey.questions:
            question_responses = [
                resp for resp in responses if resp.question_id == question.id
            ]
            
            analysis = await self.response_analyzer.analyze_question_responses(
                question, question_responses
            )
            question_analyses.append(analysis)
            
            # Collect satisfaction scores for overall calculation
            if question.category == "satisfaction":
                overall_ratings.append(analysis.satisfaction_score)
        
        # Calculate overall satisfaction
        overall_satisfaction = statistics.mean(overall_ratings) if overall_ratings else 0.0
        
        # Extract common themes across all text responses
        all_text_responses = [
            resp.response_text for resp in responses 
            if resp.response_text and resp.response_text.strip()
        ]
        
        common_themes = []
        if all_text_responses:
            themes = await self.response_analyzer.sentiment_analyzer.extract_themes(all_text_responses)
            common_themes = themes[:5]  # Top 5 themes
        
        # Generate improvement suggestions
        improvement_suggestions = await self._extract_improvement_suggestions(responses)
        
        # Extract positive highlights
        positive_highlights = await self._extract_positive_highlights(responses)
        
        # Extract concerns
        concerns_raised = await self._extract_concerns(responses)
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(question_analyses, overall_satisfaction)
        
        feedback = SessionFeedback(
            session_id=survey.session_id,
            generated_at=datetime.utcnow(),
            response_count=response_count,
            response_rate=response_rate,
            overall_satisfaction=overall_satisfaction,
            question_analyses=question_analyses,
            common_themes=common_themes,
            improvement_suggestions=improvement_suggestions,
            positive_highlights=positive_highlights,
            concerns_raised=concerns_raised,
            dm_feedback=None,  # Could be added later
            recommendations=recommendations
        )
        
        self.session_feedback[survey.session_id] = feedback
        return feedback
    
    async def _extract_improvement_suggestions(self, responses: List[SurveyResponse]) -> List[str]:
        """Extract improvement suggestions from responses"""
        suggestions = []
        
        # Look for responses to improvement-focused questions
        improvement_responses = [
            resp.response_text for resp in responses
            if (resp.response_text and 
                any(keyword in resp.response_text.lower() for keyword in [
                    "improve", "better", "suggestion", "recommend", "should", "could"
                ]))
        ]
        
        # Clean and deduplicate suggestions
        for response in improvement_responses:
            if response and len(response.strip()) > 10:  # Meaningful responses
                suggestions.append(response.strip())
        
        return suggestions[:5]  # Top 5 suggestions
    
    async def _extract_positive_highlights(self, responses: List[SurveyResponse]) -> List[str]:
        """Extract positive highlights from responses"""
        highlights = []
        
        # Look for responses with positive sentiment or highlight questions
        positive_responses = [
            resp.response_text for resp in responses
            if (resp.response_text and 
                (await self.response_analyzer.sentiment_analyzer.analyze_sentiment(resp.response_text) 
                 in [SentimentType.POSITIVE, SentimentType.VERY_POSITIVE]))
        ]
        
        # Also look for specific highlight questions
        highlight_responses = [
            resp.response_text for resp in responses
            if (resp.response_text and 
                any(keyword in resp.response_text.lower() for keyword in [
                    "favorite", "best", "loved", "enjoyed", "highlight", "amazing"
                ]))
        ]
        
        all_highlights = positive_responses + highlight_responses
        
        for response in all_highlights:
            if response and len(response.strip()) > 10:
                highlights.append(response.strip())
        
        # Remove duplicates
        unique_highlights = []
        for highlight in highlights:
            if highlight not in unique_highlights:
                unique_highlights.append(highlight)
        
        return unique_highlights[:5]  # Top 5 highlights
    
    async def _extract_concerns(self, responses: List[SurveyResponse]) -> List[str]:
        """Extract concerns from responses"""
        concerns = []
        
        # Look for negative sentiment or concern-indicating keywords
        concern_responses = [
            resp.response_text for resp in responses
            if (resp.response_text and 
                any(keyword in resp.response_text.lower() for keyword in [
                    "concern", "worried", "problem", "issue", "disappointing",
                    "frustrating", "confusing", "unclear", "difficult"
                ]))
        ]
        
        for response in concern_responses:
            if response and len(response.strip()) > 10:
                concerns.append(response.strip())
        
        return concerns[:3]  # Top 3 concerns
    
    async def _generate_recommendations(self, analyses: List[ResponseAnalysis],
                                      overall_satisfaction: float) -> List[str]:
        """Generate actionable recommendations based on feedback"""
        recommendations = []
        
        # Overall satisfaction recommendations
        if overall_satisfaction < 0.6:
            recommendations.append("Consider significant changes to session format and content based on feedback")
        elif overall_satisfaction < 0.8:
            recommendations.append("Look for specific areas to improve based on detailed feedback")
        
        # Analyze specific categories
        category_scores = defaultdict(list)
        for analysis in analyses:
            # Extract category from question (simplified)
            if "pacing" in analysis.question_text.lower():
                category_scores["pacing"].append(analysis.satisfaction_score)
            elif "story" in analysis.question_text.lower():
                category_scores["story"].append(analysis.satisfaction_score)
            elif "character" in analysis.question_text.lower():
                category_scores["character"].append(analysis.satisfaction_score)
            elif "engagement" in analysis.question_text.lower():
                category_scores["engagement"].append(analysis.satisfaction_score)
        
        # Generate category-specific recommendations
        for category, scores in category_scores.items():
            if scores and statistics.mean(scores) < 0.6:
                recommendations.append(f"Focus on improving {category} based on player feedback")
        
        # Look for common themes in negative feedback
        low_scoring_analyses = [a for a in analyses if a.satisfaction_score < 0.5]
        if len(low_scoring_analyses) > len(analyses) * 0.3:  # More than 30% low scoring
            recommendations.append("Consider discussing feedback with players directly to understand specific issues")
        
        # Engagement-specific recommendations
        engagement_analyses = [a for a in analyses if "engagement" in a.question_text.lower()]
        if engagement_analyses:
            avg_engagement = statistics.mean(a.satisfaction_score for a in engagement_analyses)
            if avg_engagement < 0.7:
                recommendations.append("Explore ways to increase player engagement through varied activities")
        
        # Default positive recommendation
        if overall_satisfaction >= 0.8:
            recommendations.append("Great session feedback! Continue current approach with minor adjustments")
        
        # Limit recommendations
        return recommendations[:5]
    
    async def get_survey(self, survey_id: str) -> Optional[Survey]:
        """Get a survey by ID"""
        return self.active_surveys.get(survey_id)
    
    async def get_session_feedback(self, session_id: str) -> Optional[SessionFeedback]:
        """Get feedback analysis for a session"""
        return self.session_feedback.get(session_id)
    
    async def get_survey_progress(self, survey_id: str) -> Dict[str, Any]:
        """Get survey response progress"""
        survey = self.active_surveys.get(survey_id)
        if not survey:
            return {}
        
        responses = self.survey_responses.get(survey_id, [])
        participants = set(resp.participant_id for resp in responses)
        
        return {
            "survey_id": survey_id,
            "responses_received": len(participants),
            "total_responses_submitted": len(responses),
            "is_active": survey.is_active,
            "expires_at": survey.expires_at,
            "time_remaining_hours": max(0, (survey.expires_at - datetime.utcnow()).total_seconds() / 3600)
        }
    
    async def close_survey(self, survey_id: str) -> bool:
        """Close a survey and prevent further responses"""
        survey = self.active_surveys.get(survey_id)
        if survey:
            survey.is_active = False
            return True
        return False
    
    async def export_survey_data(self, survey_id: str, format: str = "json") -> Optional[str]:
        """Export survey data in specified format"""
        survey = self.active_surveys.get(survey_id)
        if not survey:
            return None
        
        responses = self.survey_responses.get(survey_id, [])
        
        data = {
            "survey": {
                "id": survey.id,
                "session_id": survey.session_id,
                "title": survey.title,
                "created_at": survey.created_at.isoformat(),
                "expires_at": survey.expires_at.isoformat(),
                "questions": [
                    {
                        "id": q.id,
                        "text": q.text,
                        "type": q.question_type.value,
                        "category": q.category
                    }
                    for q in survey.questions
                ]
            },
            "responses": [
                {
                    "id": resp.id,
                    "participant_id": resp.participant_id,
                    "question_id": resp.question_id,
                    "response_value": resp.response_value,
                    "response_text": resp.response_text,
                    "submitted_at": resp.submitted_at.isoformat()
                }
                for resp in responses
            ]
        }
        
        if format == "json":
            return json.dumps(data, indent=2)
        else:
            # Could implement CSV, PDF, etc.
            return json.dumps(data, indent=2)
    
    async def get_campaign_feedback_trends(self, session_ids: List[str]) -> Dict[str, Any]:
        """Analyze feedback trends across multiple sessions"""
        trends = {
            "session_count": len(session_ids),
            "satisfaction_trend": [],
            "common_themes": defaultdict(int),
            "improvement_areas": defaultdict(int),
            "positive_trends": [],
            "concerning_trends": []
        }
        
        for session_id in session_ids:
            feedback = self.session_feedback.get(session_id)
            if feedback:
                trends["satisfaction_trend"].append(feedback.overall_satisfaction)
                
                # Aggregate themes
                for theme, count in feedback.common_themes:
                    trends["common_themes"][theme] += count
                
                # Track improvement suggestions
                for suggestion in feedback.improvement_suggestions:
                    # Simplified categorization
                    if "pacing" in suggestion.lower():
                        trends["improvement_areas"]["pacing"] += 1
                    elif "story" in suggestion.lower():
                        trends["improvement_areas"]["story"] += 1
                    elif "character" in suggestion.lower():
                        trends["improvement_areas"]["character"] += 1
        
        # Analyze satisfaction trend
        if len(trends["satisfaction_trend"]) >= 2:
            recent_avg = statistics.mean(trends["satisfaction_trend"][-3:])  # Last 3 sessions
            overall_avg = statistics.mean(trends["satisfaction_trend"])
            
            if recent_avg > overall_avg + 0.1:
                trends["positive_trends"].append("Satisfaction scores improving")
            elif recent_avg < overall_avg - 0.1:
                trends["concerning_trends"].append("Satisfaction scores declining")
        
        return trends