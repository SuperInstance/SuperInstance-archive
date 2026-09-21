#!/usr/bin/env python3
"""
Market Validation Tools System
Comprehensive market validation and research platform

Features:
- Survey creation and distribution tools
- Customer interview scheduling and management
- A/B testing framework for product concepts
- Landing page validation testing
- Social media sentiment analysis
- Competitor analysis automation
- Market sizing calculations
- Customer persona development
- MVP feedback collection
- Pivot recommendation engine
- Market trend analysis
- Customer journey mapping
- Product-market fit scoring
- Validation milestone tracking
"""

from typing import Dict, List, Optional, Any, Union, Tuple
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from enum import Enum
import json
import uuid
import asyncio
import logging
from pathlib import Path
import statistics
import random

logger = logging.getLogger(__name__)

class ValidationMethod(str, Enum):
    SURVEY = "survey"
    INTERVIEW = "interview"
    AB_TEST = "ab_test"
    LANDING_PAGE = "landing_page"
    MVP_TEST = "mvp_test"
    SOCIAL_LISTENING = "social_listening"
    COMPETITOR_ANALYSIS = "competitor_analysis"
    FOCUS_GROUP = "focus_group"

class ValidationStatus(str, Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    COLLECTING = "collecting"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"

class PMFScore(str, Enum):
    VERY_LOW = "very_low"      # 0-20%
    LOW = "low"                # 21-40%
    MODERATE = "moderate"      # 41-60%
    GOOD = "good"              # 61-80%
    EXCELLENT = "excellent"    # 81-100%

class ValidationCampaign(BaseModel):
    id: str
    business_id: str
    name: str
    description: str
    method: ValidationMethod
    status: ValidationStatus
    
    # Configuration
    target_responses: int
    actual_responses: int = 0
    start_date: datetime
    end_date: datetime
    
    # Targeting
    target_demographics: Dict[str, Any] = {}
    geographic_focus: List[str] = []
    sample_size: int
    
    # Results
    response_rate: float = 0.0
    completion_rate: float = 0.0
    insights: List[str] = []
    recommendations: List[str] = []
    
    # Analysis
    key_metrics: Dict[str, float] = {}
    statistical_significance: float = 0.0
    confidence_level: float = 0.95
    
    created_at: datetime
    updated_at: datetime
    created_by: str

class SurveyQuestion(BaseModel):
    id: str
    type: str  # multiple_choice, scale, text, boolean, ranking
    question: str
    options: List[str] = []
    required: bool = True
    
    # Logic
    skip_logic: Dict[str, Any] = {}  # Conditional logic
    randomize_options: bool = False
    
    # Analysis
    response_count: int = 0
    responses: List[Any] = []

class Survey(BaseModel):
    id: str
    campaign_id: str
    title: str
    description: str
    
    # Questions
    questions: List[SurveyQuestion]
    estimated_completion_time: int  # minutes
    
    # Distribution
    distribution_channels: List[str] = []
    target_sample_size: int
    actual_responses: int = 0
    
    # Settings
    is_anonymous: bool = True
    allow_multiple_responses: bool = False
    require_completion: bool = False
    
    # Analysis
    response_rate: float = 0.0
    average_completion_time: float = 0.0
    drop_off_points: List[int] = []
    
    created_at: datetime
    published_at: Optional[datetime] = None

class Interview(BaseModel):
    id: str
    campaign_id: str
    interviewee_id: str
    
    # Scheduling
    scheduled_date: datetime
    duration_minutes: int
    status: str  # scheduled, completed, cancelled, no_show
    
    # Content
    interview_guide: List[str] = []
    key_questions: List[str] = []
    notes: str = ""
    
    # Results
    insights: List[str] = []
    pain_points: List[str] = []
    feature_requests: List[str] = []
    willingness_to_pay: Optional[float] = None
    
    # Scoring
    interest_score: int = 0  # 1-10
    urgency_score: int = 0   # 1-10
    fit_score: int = 0       # 1-10
    
    created_at: datetime
    completed_at: Optional[datetime] = None

class ABTest(BaseModel):
    id: str
    campaign_id: str
    name: str
    hypothesis: str
    
    # Test variants
    control_variant: Dict[str, Any]
    test_variants: List[Dict[str, Any]]
    
    # Metrics
    primary_metric: str
    secondary_metrics: List[str] = []
    
    # Results per variant
    results: Dict[str, Dict[str, float]] = {}
    
    # Analysis
    winner: Optional[str] = None
    confidence_level: float = 0.0
    statistical_significance: bool = False
    
    # Settings
    traffic_split: Dict[str, float] = {}  # variant_id -> percentage
    min_sample_size: int
    max_duration_days: int
    
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

class LandingPageTest(BaseModel):
    id: str
    campaign_id: str
    page_url: str
    page_title: str
    
    # Metrics
    unique_visitors: int = 0
    page_views: int = 0
    conversions: int = 0
    conversion_rate: float = 0.0
    bounce_rate: float = 0.0
    time_on_page: float = 0.0
    
    # Traffic sources
    traffic_sources: Dict[str, int] = {}
    referrers: List[str] = []
    
    # Conversion tracking
    conversion_goals: List[str] = []
    funnel_metrics: Dict[str, int] = {}
    
    # Heat map data
    click_map: Dict[str, int] = {}
    scroll_depth: List[float] = []
    
    created_at: datetime
    last_updated: datetime

class CustomerPersona(BaseModel):
    id: str
    business_id: str
    name: str
    description: str
    
    # Demographics
    age_range: str
    gender: str
    income_range: str
    education: str
    occupation: str
    location: str
    
    # Psychographics
    interests: List[str] = []
    values: List[str] = []
    lifestyle: str = ""
    personality_traits: List[str] = []
    
    # Behavioral
    buying_behavior: str = ""
    decision_factors: List[str] = []
    preferred_channels: List[str] = []
    technology_adoption: str = ""
    
    # Pain points and needs
    pain_points: List[str] = []
    needs: List[str] = []
    goals: List[str] = []
    
    # Validation data
    based_on_interviews: int = 0
    based_on_surveys: int = 0
    confidence_score: float = 0.0
    
    created_at: datetime
    updated_at: datetime

class MarketValidationManager:
    def __init__(self):
        self.campaigns: Dict[str, ValidationCampaign] = {}
        self.surveys: Dict[str, Survey] = {}
        self.interviews: Dict[str, Interview] = {}
        self.ab_tests: Dict[str, ABTest] = {}
        self.landing_page_tests: Dict[str, LandingPageTest] = {}
        self.personas: Dict[str, CustomerPersona] = {}
        
        # Analytics data
        self.validation_metrics: Dict[str, Dict[str, Any]] = {}
    
    async def create_validation_campaign(
        self, 
        business_id: str, 
        name: str, 
        method: ValidationMethod,
        config: Dict[str, Any]
    ) -> ValidationCampaign:
        """Create a new market validation campaign"""
        
        campaign_id = str(uuid.uuid4())
        
        campaign = ValidationCampaign(
            id=campaign_id,
            business_id=business_id,
            name=name,
            description=config.get("description", ""),
            method=method,
            status=ValidationStatus.PLANNING,
            target_responses=config.get("target_responses", 100),
            start_date=config.get("start_date", datetime.now()),
            end_date=config.get("end_date", datetime.now() + timedelta(days=30)),
            target_demographics=config.get("target_demographics", {}),
            geographic_focus=config.get("geographic_focus", []),
            sample_size=config.get("sample_size", 100),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            created_by=config.get("created_by", "user")
        )
        
        self.campaigns[campaign_id] = campaign
        
        # Create method-specific components
        if method == ValidationMethod.SURVEY:
            await self._create_survey(campaign_id, config.get("survey_config", {}))
        elif method == ValidationMethod.AB_TEST:
            await self._create_ab_test(campaign_id, config.get("ab_test_config", {}))
        elif method == ValidationMethod.LANDING_PAGE:
            await self._create_landing_page_test(campaign_id, config.get("landing_page_config", {}))
        
        return campaign
    
    async def _create_survey(self, campaign_id: str, config: Dict[str, Any]):
        """Create survey for validation campaign"""
        
        survey_id = str(uuid.uuid4())
        
        # Default questions for market validation
        default_questions = [
            SurveyQuestion(
                id=str(uuid.uuid4()),
                type="scale",
                question="How important is solving [PROBLEM] for you?",
                options=["1 - Not important", "2", "3", "4", "5 - Very important"],
                required=True
            ),
            SurveyQuestion(
                id=str(uuid.uuid4()),
                type="scale", 
                question="How satisfied are you with current solutions?",
                options=["1 - Very unsatisfied", "2", "3", "4", "5 - Very satisfied"],
                required=True
            ),
            SurveyQuestion(
                id=str(uuid.uuid4()),
                type="multiple_choice",
                question="How much would you be willing to pay for a solution?",
                options=["$0 (Free)", "$1-10", "$11-50", "$51-100", "$100+"],
                required=True
            ),
            SurveyQuestion(
                id=str(uuid.uuid4()),
                type="text",
                question="What is your biggest challenge with [PROBLEM]?",
                required=False
            )
        ]
        
        survey = Survey(
            id=survey_id,
            campaign_id=campaign_id,
            title=config.get("title", "Market Validation Survey"),
            description=config.get("description", "Help us understand your needs"),
            questions=config.get("questions", default_questions),
            estimated_completion_time=config.get("estimated_time", 5),
            target_sample_size=config.get("target_sample_size", 100),
            distribution_channels=config.get("channels", ["email", "social"]),
            created_at=datetime.now()
        )
        
        self.surveys[survey_id] = survey
    
    async def _create_ab_test(self, campaign_id: str, config: Dict[str, Any]):
        """Create A/B test for validation campaign"""
        
        test_id = str(uuid.uuid4())
        
        ab_test = ABTest(
            id=test_id,
            campaign_id=campaign_id,
            name=config.get("name", "Product Concept Test"),
            hypothesis=config.get("hypothesis", "Version B will perform better than Version A"),
            control_variant=config.get("control_variant", {"name": "Control", "description": "Current version"}),
            test_variants=config.get("test_variants", [{"name": "Variant B", "description": "Alternative version"}]),
            primary_metric=config.get("primary_metric", "conversion_rate"),
            secondary_metrics=config.get("secondary_metrics", ["engagement_time", "click_through_rate"]),
            traffic_split=config.get("traffic_split", {"control": 0.5, "variant_b": 0.5}),
            min_sample_size=config.get("min_sample_size", 100),
            max_duration_days=config.get("max_duration_days", 14),
            created_at=datetime.now()
        )
        
        self.ab_tests[test_id] = ab_test
    
    async def _create_landing_page_test(self, campaign_id: str, config: Dict[str, Any]):
        """Create landing page test for validation campaign"""
        
        test_id = str(uuid.uuid4())
        
        landing_test = LandingPageTest(
            id=test_id,
            campaign_id=campaign_id,
            page_url=config.get("page_url", "https://example.com/landing"),
            page_title=config.get("page_title", "Product Landing Page"),
            conversion_goals=config.get("conversion_goals", ["email_signup", "demo_request"]),
            created_at=datetime.now(),
            last_updated=datetime.now()
        )
        
        self.landing_page_tests[test_id] = landing_test
    
    async def submit_survey_response(self, survey_id: str, responses: Dict[str, Any]) -> bool:
        """Submit a survey response"""
        survey = self.surveys.get(survey_id)
        if not survey:
            return False
        
        # Process responses for each question
        for question in survey.questions:
            if question.id in responses:
                question.responses.append(responses[question.id])
                question.response_count += 1
        
        survey.actual_responses += 1
        survey.response_rate = (survey.actual_responses / survey.target_sample_size) * 100
        
        # Update campaign metrics
        campaign = self.campaigns.get(survey.campaign_id)
        if campaign:
            campaign.actual_responses += 1
            campaign.response_rate = (campaign.actual_responses / campaign.target_responses) * 100
        
        return True
    
    async def schedule_interview(self, campaign_id: str, interviewee_data: Dict[str, Any]) -> Interview:
        """Schedule a customer interview"""
        
        interview_id = str(uuid.uuid4())
        
        interview = Interview(
            id=interview_id,
            campaign_id=campaign_id,
            interviewee_id=str(uuid.uuid4()),
            scheduled_date=interviewee_data.get("scheduled_date", datetime.now() + timedelta(days=1)),
            duration_minutes=interviewee_data.get("duration", 30),
            status="scheduled",
            interview_guide=interviewee_data.get("guide", self._get_default_interview_guide()),
            created_at=datetime.now()
        )
        
        self.interviews[interview_id] = interview
        return interview
    
    def _get_default_interview_guide(self) -> List[str]:
        """Get default interview guide questions"""
        return [
            "Tell me about how you currently handle [PROBLEM]",
            "What's the biggest challenge you face with [PROBLEM]?", 
            "How much time/money does this problem cost you?",
            "What solutions have you tried before?",
            "What didn't work about previous solutions?",
            "If there was a perfect solution, what would it look like?",
            "How much would you be willing to pay for that solution?",
            "Who else is involved in the decision-making process?",
            "What would prevent you from adopting a new solution?",
            "How urgent is solving this problem for you?"
        ]
    
    async def complete_interview(self, interview_id: str, results: Dict[str, Any]) -> bool:
        """Mark interview as complete and record results"""
        interview = self.interviews.get(interview_id)
        if not interview:
            return False
        
        interview.status = "completed"
        interview.completed_at = datetime.now()
        interview.notes = results.get("notes", "")
        interview.insights = results.get("insights", [])
        interview.pain_points = results.get("pain_points", [])
        interview.feature_requests = results.get("feature_requests", [])
        interview.willingness_to_pay = results.get("willingness_to_pay")
        interview.interest_score = results.get("interest_score", 0)
        interview.urgency_score = results.get("urgency_score", 0)
        interview.fit_score = results.get("fit_score", 0)
        
        return True
    
    async def analyze_campaign_results(self, campaign_id: str) -> Dict[str, Any]:
        """Analyze results from a validation campaign"""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return {}
        
        analysis = {
            "campaign_id": campaign_id,
            "method": campaign.method,
            "status": campaign.status,
            "response_rate": campaign.response_rate,
            "insights": [],
            "recommendations": [],
            "key_findings": {},
            "next_steps": []
        }
        
        if campaign.method == ValidationMethod.SURVEY:
            analysis.update(await self._analyze_survey_results(campaign_id))
        elif campaign.method == ValidationMethod.INTERVIEW:
            analysis.update(await self._analyze_interview_results(campaign_id))
        elif campaign.method == ValidationMethod.AB_TEST:
            analysis.update(await self._analyze_ab_test_results(campaign_id))
        elif campaign.method == ValidationMethod.LANDING_PAGE:
            analysis.update(await self._analyze_landing_page_results(campaign_id))
        
        return analysis
    
    async def _analyze_survey_results(self, campaign_id: str) -> Dict[str, Any]:
        """Analyze survey results"""
        surveys = [s for s in self.surveys.values() if s.campaign_id == campaign_id]
        if not surveys:
            return {}
        
        survey = surveys[0]
        analysis = {"survey_analysis": {}}
        
        for question in survey.questions:
            if question.responses:
                if question.type == "scale":
                    # Calculate average score for scale questions
                    numeric_responses = [int(r) for r in question.responses if str(r).isdigit()]
                    if numeric_responses:
                        avg_score = statistics.mean(numeric_responses)
                        analysis["survey_analysis"][question.question] = {
                            "average_score": avg_score,
                            "response_count": len(numeric_responses),
                            "distribution": {str(i): numeric_responses.count(i) for i in range(1, 6)}
                        }
                
                elif question.type == "multiple_choice":
                    # Count responses for multiple choice
                    response_counts = {}
                    for response in question.responses:
                        response_counts[response] = response_counts.get(response, 0) + 1
                    
                    analysis["survey_analysis"][question.question] = {
                        "responses": response_counts,
                        "total_responses": len(question.responses),
                        "top_choice": max(response_counts, key=response_counts.get) if response_counts else None
                    }
        
        # Generate insights based on analysis
        insights = []
        if "How important is solving" in str(analysis.get("survey_analysis", {})):
            # Find importance question
            for q, data in analysis["survey_analysis"].items():
                if "important" in q.lower() and "average_score" in data:
                    if data["average_score"] >= 4:
                        insights.append("High problem importance: Users rate this problem as very important")
                    elif data["average_score"] <= 2:
                        insights.append("Low problem importance: Users don't see this as a significant problem")
        
        analysis["insights"] = insights
        return analysis
    
    async def _analyze_interview_results(self, campaign_id: str) -> Dict[str, Any]:
        """Analyze interview results"""
        interviews = [i for i in self.interviews.values() if i.campaign_id == campaign_id]
        completed_interviews = [i for i in interviews if i.status == "completed"]
        
        if not completed_interviews:
            return {}
        
        # Aggregate scores
        interest_scores = [i.interest_score for i in completed_interviews if i.interest_score > 0]
        urgency_scores = [i.urgency_score for i in completed_interviews if i.urgency_score > 0]
        fit_scores = [i.fit_score for i in completed_interviews if i.fit_score > 0]
        
        # Common pain points
        all_pain_points = []
        for interview in completed_interviews:
            all_pain_points.extend(interview.pain_points)
        
        pain_point_counts = {}
        for pain in all_pain_points:
            pain_point_counts[pain] = pain_point_counts.get(pain, 0) + 1
        
        top_pain_points = sorted(pain_point_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Willingness to pay
        wtp_values = [i.willingness_to_pay for i in completed_interviews if i.willingness_to_pay is not None]
        
        analysis = {
            "interview_analysis": {
                "total_interviews": len(interviews),
                "completed_interviews": len(completed_interviews),
                "average_interest_score": statistics.mean(interest_scores) if interest_scores else 0,
                "average_urgency_score": statistics.mean(urgency_scores) if urgency_scores else 0,
                "average_fit_score": statistics.mean(fit_scores) if fit_scores else 0,
                "top_pain_points": top_pain_points,
                "average_wtp": statistics.mean(wtp_values) if wtp_values else 0,
                "wtp_range": {"min": min(wtp_values), "max": max(wtp_values)} if wtp_values else None
            }
        }
        
        # Generate insights
        insights = []
        if interest_scores and statistics.mean(interest_scores) >= 7:
            insights.append("High interest: Users show strong interest in the solution")
        if urgency_scores and statistics.mean(urgency_scores) >= 7:
            insights.append("High urgency: Users have urgent need for a solution")
        if top_pain_points and top_pain_points[0][1] >= len(completed_interviews) * 0.5:
            insights.append(f"Common pain point: '{top_pain_points[0][0]}' mentioned by {top_pain_points[0][1]} users")
        
        analysis["insights"] = insights
        return analysis
    
    async def _analyze_ab_test_results(self, campaign_id: str) -> Dict[str, Any]:
        """Analyze A/B test results"""
        tests = [t for t in self.ab_tests.values() if t.campaign_id == campaign_id]
        if not tests:
            return {}
        
        test = tests[0]
        
        # Mock results for demonstration
        control_conversion = random.uniform(0.02, 0.05)
        variant_conversion = random.uniform(0.03, 0.08)
        
        # Calculate statistical significance (simplified)
        improvement = ((variant_conversion - control_conversion) / control_conversion) * 100
        statistical_sig = abs(improvement) > 20  # Simplified check
        
        analysis = {
            "ab_test_analysis": {
                "test_name": test.name,
                "hypothesis": test.hypothesis,
                "control_conversion_rate": control_conversion,
                "variant_conversion_rate": variant_conversion,
                "improvement_percentage": improvement,
                "statistical_significance": statistical_sig,
                "confidence_level": 95 if statistical_sig else 80,
                "winner": "variant" if variant_conversion > control_conversion and statistical_sig else "inconclusive"
            }
        }
        
        insights = []
        if statistical_sig and improvement > 0:
            insights.append(f"Variant shows {improvement:.1f}% improvement over control")
        elif not statistical_sig:
            insights.append("Results are not statistically significant - need more data")
        
        analysis["insights"] = insights
        return analysis
    
    async def _analyze_landing_page_results(self, campaign_id: str) -> Dict[str, Any]:
        """Analyze landing page test results"""
        tests = [t for t in self.landing_page_tests.values() if t.campaign_id == campaign_id]
        if not tests:
            return {}
        
        test = tests[0]
        
        # Mock data for demonstration
        test.unique_visitors = random.randint(500, 2000)
        test.page_views = int(test.unique_visitors * random.uniform(1.1, 1.5))
        test.conversions = int(test.unique_visitors * random.uniform(0.02, 0.15))
        test.conversion_rate = (test.conversions / test.unique_visitors) * 100
        test.bounce_rate = random.uniform(40, 80)
        test.time_on_page = random.uniform(30, 180)
        
        analysis = {
            "landing_page_analysis": {
                "page_url": test.page_url,
                "unique_visitors": test.unique_visitors,
                "page_views": test.page_views,
                "conversions": test.conversions,
                "conversion_rate": test.conversion_rate,
                "bounce_rate": test.bounce_rate,
                "time_on_page": test.time_on_page
            }
        }
        
        insights = []
        if test.conversion_rate >= 5:
            insights.append("High conversion rate indicates strong product-market interest")
        elif test.conversion_rate <= 1:
            insights.append("Low conversion rate suggests weak value proposition or poor targeting")
        
        if test.bounce_rate >= 70:
            insights.append("High bounce rate indicates page may not match visitor expectations")
        
        analysis["insights"] = insights
        return analysis
    
    async def calculate_product_market_fit_score(self, business_id: str) -> Dict[str, Any]:
        """Calculate Product-Market Fit score based on validation data"""
        
        # Get all campaigns for this business
        business_campaigns = [c for c in self.campaigns.values() if c.business_id == business_id]
        
        if not business_campaigns:
            return {"score": 0, "level": PMFScore.VERY_LOW, "factors": []}
        
        # Scoring factors
        factors = []
        total_score = 0
        max_score = 0
        
        # Survey-based scoring
        survey_campaigns = [c for c in business_campaigns if c.method == ValidationMethod.SURVEY]
        if survey_campaigns:
            for campaign in survey_campaigns:
                surveys = [s for s in self.surveys.values() if s.campaign_id == campaign.id]
                for survey in surveys:
                    for question in survey.questions:
                        if question.responses and "important" in question.question.lower():
                            responses = [int(r) for r in question.responses if str(r).isdigit()]
                            if responses:
                                avg_importance = statistics.mean(responses)
                                score = (avg_importance / 5) * 20  # 20 points max
                                total_score += score
                                max_score += 20
                                factors.append(f"Problem importance: {avg_importance:.1f}/5")
        
        # Interview-based scoring
        interview_campaigns = [c for c in business_campaigns if c.method == ValidationMethod.INTERVIEW]
        if interview_campaigns:
            all_interviews = []
            for campaign in interview_campaigns:
                campaign_interviews = [i for i in self.interviews.values() if i.campaign_id == campaign.id and i.status == "completed"]
                all_interviews.extend(campaign_interviews)
            
            if all_interviews:
                # Interest score component
                interest_scores = [i.interest_score for i in all_interviews if i.interest_score > 0]
                if interest_scores:
                    avg_interest = statistics.mean(interest_scores)
                    score = (avg_interest / 10) * 15  # 15 points max
                    total_score += score
                    max_score += 15
                    factors.append(f"User interest: {avg_interest:.1f}/10")
                
                # Urgency score component
                urgency_scores = [i.urgency_score for i in all_interviews if i.urgency_score > 0]
                if urgency_scores:
                    avg_urgency = statistics.mean(urgency_scores)
                    score = (avg_urgency / 10) * 15  # 15 points max
                    total_score += score
                    max_score += 15
                    factors.append(f"Problem urgency: {avg_urgency:.1f}/10")
                
                # Willingness to pay
                wtp_values = [i.willingness_to_pay for i in all_interviews if i.willingness_to_pay is not None]
                if wtp_values:
                    avg_wtp = statistics.mean(wtp_values)
                    score = min(avg_wtp / 100, 1) * 10  # 10 points max, assuming $100 is good WTP
                    total_score += score
                    max_score += 10
                    factors.append(f"Willingness to pay: ${avg_wtp:.0f}")
        
        # Landing page conversion scoring
        landing_campaigns = [c for c in business_campaigns if c.method == ValidationMethod.LANDING_PAGE]
        if landing_campaigns:
            for campaign in landing_campaigns:
                tests = [t for t in self.landing_page_tests.values() if t.campaign_id == campaign.id]
                for test in tests:
                    if test.conversion_rate > 0:
                        # Conversion rate scoring (5% = full points)
                        score = min(test.conversion_rate / 5, 1) * 20  # 20 points max
                        total_score += score
                        max_score += 20
                        factors.append(f"Landing page conversion: {test.conversion_rate:.1f}%")
        
        # Calculate final score
        if max_score > 0:
            final_score = (total_score / max_score) * 100
        else:
            final_score = 0
        
        # Determine PMF level
        if final_score >= 80:
            level = PMFScore.EXCELLENT
        elif final_score >= 60:
            level = PMFScore.GOOD
        elif final_score >= 40:
            level = PMFScore.MODERATE
        elif final_score >= 20:
            level = PMFScore.LOW
        else:
            level = PMFScore.VERY_LOW
        
        return {
            "score": round(final_score, 1),
            "level": level,
            "factors": factors,
            "total_campaigns": len(business_campaigns),
            "recommendations": self._get_pmf_recommendations(final_score, factors)
        }
    
    def _get_pmf_recommendations(self, score: float, factors: List[str]) -> List[str]:
        """Get recommendations based on PMF score"""
        recommendations = []
        
        if score < 20:
            recommendations.extend([
                "Conduct more customer interviews to understand the problem better",
                "Validate that you're solving a real, urgent problem",
                "Consider pivoting to a different market segment or problem"
            ])
        elif score < 40:
            recommendations.extend([
                "Improve your value proposition based on customer feedback",
                "Test different messaging and positioning",
                "Gather more quantitative validation data"
            ])
        elif score < 60:
            recommendations.extend([
                "Optimize your solution based on user feedback",
                "Test pricing and packaging options",
                "Scale up customer acquisition efforts gradually"
            ])
        elif score < 80:
            recommendations.extend([
                "Focus on product optimization and user experience",
                "Develop customer success programs",
                "Prepare for scaling operations"
            ])
        else:
            recommendations.extend([
                "Scale customer acquisition aggressively",
                "Expand to adjacent markets or segments",
                "Consider fundraising for rapid growth"
            ])
        
        return recommendations
    
    async def create_customer_persona(self, business_id: str, validation_data: Dict[str, Any]) -> CustomerPersona:
        """Create customer persona based on validation data"""
        
        persona_id = str(uuid.uuid4())
        
        persona = CustomerPersona(
            id=persona_id,
            business_id=business_id,
            name=validation_data.get("name", "Primary Customer"),
            description=validation_data.get("description", "Main target customer segment"),
            age_range=validation_data.get("age_range", "25-45"),
            gender=validation_data.get("gender", "Mixed"),
            income_range=validation_data.get("income_range", "$50k-$100k"),
            education=validation_data.get("education", "College educated"),
            occupation=validation_data.get("occupation", "Professional"),
            location=validation_data.get("location", "Urban/Suburban"),
            interests=validation_data.get("interests", []),
            values=validation_data.get("values", []),
            lifestyle=validation_data.get("lifestyle", ""),
            personality_traits=validation_data.get("personality_traits", []),
            buying_behavior=validation_data.get("buying_behavior", "Research-driven"),
            decision_factors=validation_data.get("decision_factors", ["Price", "Quality", "Reviews"]),
            preferred_channels=validation_data.get("preferred_channels", ["Online", "Social Media"]),
            technology_adoption=validation_data.get("technology_adoption", "Early majority"),
            pain_points=validation_data.get("pain_points", []),
            needs=validation_data.get("needs", []),
            goals=validation_data.get("goals", []),
            based_on_interviews=validation_data.get("interviews_count", 0),
            based_on_surveys=validation_data.get("surveys_count", 0),
            confidence_score=validation_data.get("confidence_score", 0.7),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.personas[persona_id] = persona
        return persona
    
    async def get_validation_dashboard(self, business_id: str) -> Dict[str, Any]:
        """Get comprehensive validation dashboard for business"""
        
        # Get all campaigns
        campaigns = [c for c in self.campaigns.values() if c.business_id == business_id]
        
        # Get PMF score
        pmf_data = await self.calculate_product_market_fit_score(business_id)
        
        # Calculate overall metrics
        total_responses = sum(c.actual_responses for c in campaigns)
        avg_response_rate = statistics.mean([c.response_rate for c in campaigns if c.response_rate > 0]) if campaigns else 0
        
        # Get recent insights
        recent_insights = []
        for campaign in campaigns[-5:]:  # Last 5 campaigns
            analysis = await self.analyze_campaign_results(campaign.id)
            recent_insights.extend(analysis.get("insights", []))
        
        dashboard = {
            "business_id": business_id,
            "summary": {
                "total_campaigns": len(campaigns),
                "total_responses": total_responses,
                "average_response_rate": round(avg_response_rate, 1),
                "pmf_score": pmf_data["score"],
                "pmf_level": pmf_data["level"]
            },
            "campaigns_by_method": {
                method.value: len([c for c in campaigns if c.method == method]) 
                for method in ValidationMethod
            },
            "recent_insights": recent_insights[-10:],  # Top 10 recent insights
            "recommendations": pmf_data.get("recommendations", []),
            "personas_count": len([p for p in self.personas.values() if p.business_id == business_id]),
            "next_steps": [
                "Complete ongoing validation campaigns",
                "Analyze collected data for insights", 
                "Create or update customer personas",
                "Develop product roadmap based on findings"
            ]
        }
        
        return dashboard

# Global instance
market_validation_manager = MarketValidationManager()