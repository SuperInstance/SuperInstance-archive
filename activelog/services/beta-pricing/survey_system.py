"""
Survey System for Price Sensitivity Analysis
Collect user feedback and analyze price sensitivity to optimize pricing strategies
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import sqlite3
import json
import uuid
import statistics
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class SurveyType(str, Enum):
    PRICE_SENSITIVITY = "price_sensitivity"
    FEATURE_VALUE = "feature_value"
    WILLINGNESS_TO_PAY = "willingness_to_pay"
    COMPETITOR_COMPARISON = "competitor_comparison"
    SATISFACTION = "satisfaction"

class QuestionType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    SCALE = "scale"
    OPEN_TEXT = "open_text"
    PRICE_POINT = "price_point"
    RANKING = "ranking"

@dataclass
class SurveyQuestion:
    question_id: str
    question_type: QuestionType
    question_text: str
    options: List[str]
    required: bool
    weight: float = 1.0

@dataclass
class PriceSensitivityMetrics:
    optimal_price_point: Decimal
    price_elasticity: float
    demand_curve: List[Dict[str, float]]
    sensitivity_score: float
    willingness_to_pay_distribution: List[float]

class PricingSurveySystem:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/beta-pricing/data/beta_pricing.db"
        self._initialize_tables()
        
        # Pre-defined survey templates
        self.survey_templates = {
            "price_sensitivity": self._get_price_sensitivity_template(),
            "feature_value": self._get_feature_value_template(),
            "willingness_to_pay": self._get_willingness_to_pay_template()
        }
    
    def _initialize_tables(self):
        """Initialize database tables for surveys"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Surveys table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pricing_surveys (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                survey_type TEXT NOT NULL,
                questions TEXT NOT NULL,
                target_users TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                data TEXT NOT NULL
            )
        ''')
        
        # Survey responses table (already exists in main.py, ensuring completeness)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS survey_responses (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                survey_id TEXT NOT NULL,
                survey_type TEXT NOT NULL,
                questions_responses TEXT NOT NULL,
                price_sensitivity_score DECIMAL,
                willingness_to_pay DECIMAL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completion_time_seconds INTEGER,
                data TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES beta_users (id),
                FOREIGN KEY (survey_id) REFERENCES pricing_surveys (id)
            )
        ''')
        
        # Price sensitivity analysis table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_sensitivity_analysis (
                id TEXT PRIMARY KEY,
                analysis_date DATE NOT NULL,
                user_segment TEXT,
                optimal_price DECIMAL NOT NULL,
                price_elasticity REAL NOT NULL,
                sensitivity_score REAL NOT NULL,
                sample_size INTEGER NOT NULL,
                confidence_level REAL NOT NULL,
                data TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _get_price_sensitivity_template(self) -> List[SurveyQuestion]:
        """Get price sensitivity survey template"""
        return [
            SurveyQuestion(
                question_id="PS001",
                question_type=QuestionType.SCALE,
                question_text="How likely are you to purchase our service at $29/month?",
                options=["1 - Very Unlikely", "2 - Unlikely", "3 - Neutral", "4 - Likely", "5 - Very Likely"],
                required=True,
                weight=2.0
            ),
            SurveyQuestion(
                question_id="PS002",
                question_type=QuestionType.SCALE,
                question_text="How likely are you to purchase our service at $49/month?",
                options=["1 - Very Unlikely", "2 - Unlikely", "3 - Neutral", "4 - Likely", "5 - Very Likely"],
                required=True,
                weight=2.0
            ),
            SurveyQuestion(
                question_id="PS003",
                question_type=QuestionType.SCALE,
                question_text="How likely are you to purchase our service at $99/month?",
                options=["1 - Very Unlikely", "2 - Unlikely", "3 - Neutral", "4 - Likely", "5 - Very Likely"],
                required=True,
                weight=2.0
            ),
            SurveyQuestion(
                question_id="PS004",
                question_type=QuestionType.PRICE_POINT,
                question_text="What is the maximum amount you would pay monthly for this service?",
                options=[],
                required=True,
                weight=3.0
            ),
            SurveyQuestion(
                question_id="PS005",
                question_type=QuestionType.MULTIPLE_CHOICE,
                question_text="Which factor most influences your pricing decisions?",
                options=["Feature set", "Brand reputation", "Support quality", "Integration capabilities", "Competitor pricing"],
                required=True,
                weight=1.0
            )
        ]
    
    def _get_feature_value_template(self) -> List[SurveyQuestion]:
        """Get feature value survey template"""
        return [
            SurveyQuestion(
                question_id="FV001",
                question_type=QuestionType.RANKING,
                question_text="Rank these features by importance to you:",
                options=["Advanced Analytics", "API Access", "Priority Support", "Custom Integrations", "White Label"],
                required=True,
                weight=2.0
            ),
            SurveyQuestion(
                question_id="FV002",
                question_type=QuestionType.SCALE,
                question_text="How much additional value does Priority Support add?",
                options=["0% - No additional value", "10% - Minimal value", "25% - Some value", "50% - Significant value", "100% - Essential feature"],
                required=True,
                weight=1.5
            ),
            SurveyQuestion(
                question_id="FV003",
                question_type=QuestionType.PRICE_POINT,
                question_text="How much extra would you pay for Advanced Analytics?",
                options=[],
                required=True,
                weight=2.0
            )
        ]
    
    def _get_willingness_to_pay_template(self) -> List[SurveyQuestion]:
        """Get willingness to pay survey template"""
        return [
            SurveyQuestion(
                question_id="WTP001",
                question_type=QuestionType.MULTIPLE_CHOICE,
                question_text="Which pricing model do you prefer?",
                options=["Monthly subscription", "Annual subscription (discount)", "Pay-per-use", "One-time purchase", "Freemium with upgrades"],
                required=True,
                weight=1.0
            ),
            SurveyQuestion(
                question_id="WTP002",
                question_type=QuestionType.SCALE,
                question_text="At what price would this service become too expensive?",
                options=["Under $20", "$20-40", "$40-80", "$80-150", "Over $150"],
                required=True,
                weight=2.0
            ),
            SurveyQuestion(
                question_id="WTP003",
                question_type=QuestionType.PRICE_POINT,
                question_text="What would you consider a fair price for this service?",
                options=[],
                required=True,
                weight=3.0
            )
        ]
    
    async def create_survey(
        self,
        title: str,
        survey_type: SurveyType = SurveyType.PRICE_SENSITIVITY,
        custom_questions: Optional[List[Dict[str, Any]]] = None,
        target_users: Optional[List[str]] = None,
        expires_in_days: int = 30
    ) -> Dict[str, Any]:
        """Create a new pricing survey"""
        try:
            survey_id = f"SURVEY_{uuid.uuid4().hex[:8].upper()}"
            
            # Use template or custom questions
            if custom_questions:
                questions = []
                for q_data in custom_questions:
                    question = SurveyQuestion(
                        question_id=q_data.get("question_id", f"Q{len(questions)+1:03d}"),
                        question_type=QuestionType(q_data["question_type"]),
                        question_text=q_data["question_text"],
                        options=q_data.get("options", []),
                        required=q_data.get("required", True),
                        weight=q_data.get("weight", 1.0)
                    )
                    questions.append(question)
            else:
                questions = self.survey_templates.get(survey_type.value, self.survey_templates["price_sensitivity"])
            
            expires_at = datetime.now() + timedelta(days=expires_in_days)
            
            survey_data = {
                "id": survey_id,
                "title": title,
                "survey_type": survey_type.value,
                "questions": [
                    {
                        "question_id": q.question_id,
                        "question_type": q.question_type.value,
                        "question_text": q.question_text,
                        "options": q.options,
                        "required": q.required,
                        "weight": q.weight
                    }
                    for q in questions
                ],
                "target_users": target_users or [],
                "created_at": datetime.now().isoformat(),
                "expires_at": expires_at.isoformat()
            }
            
            # Store survey
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO pricing_surveys 
                (id, title, survey_type, questions, target_users, expires_at, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                survey_id, title, survey_type.value,
                json.dumps(survey_data["questions"]),
                json.dumps(target_users or []),
                expires_at.isoformat(),
                json.dumps(survey_data)
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Created survey {survey_id}: {title}")
            
            return survey_data
            
        except Exception as e:
            logger.error(f"Error creating survey: {str(e)}")
            return {"error": str(e)}
    
    async def get_survey(self, survey_id: str) -> Dict[str, Any]:
        """Get survey details"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT data FROM pricing_surveys WHERE id = ?
            ''', (survey_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return {"error": "Survey not found"}
            
            return json.loads(result[0])
            
        except Exception as e:
            logger.error(f"Error getting survey: {str(e)}")
            return {"error": str(e)}
    
    async def submit_response(
        self,
        survey_id: str,
        user_id: str,
        responses: Dict[str, Any],
        completion_time_seconds: int = 0
    ) -> Dict[str, Any]:
        """Submit survey response and analyze price sensitivity"""
        try:
            # Get survey details
            survey_data = await self.get_survey(survey_id)
            if "error" in survey_data:
                return survey_data
            
            response_id = f"RESP_{uuid.uuid4().hex[:8].upper()}"
            
            # Analyze price sensitivity from responses
            sensitivity_analysis = self._analyze_price_sensitivity(responses, survey_data)
            
            response_data = {
                "id": response_id,
                "survey_id": survey_id,
                "user_id": user_id,
                "responses": responses,
                "price_sensitivity_score": sensitivity_analysis.get("sensitivity_score"),
                "willingness_to_pay": sensitivity_analysis.get("willingness_to_pay"),
                "submitted_at": datetime.now().isoformat(),
                "completion_time_seconds": completion_time_seconds
            }
            
            # Store response
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO survey_responses 
                (id, user_id, survey_id, survey_type, questions_responses,
                 price_sensitivity_score, willingness_to_pay, completion_time_seconds, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                response_id, user_id, survey_id, survey_data["survey_type"],
                json.dumps(responses),
                sensitivity_analysis.get("sensitivity_score"),
                sensitivity_analysis.get("willingness_to_pay"),
                completion_time_seconds,
                json.dumps(response_data)
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Submitted survey response {response_id} for user {user_id}")
            
            return {
                "response_id": response_id,
                "submitted": True,
                "analysis": sensitivity_analysis
            }
            
        except Exception as e:
            logger.error(f"Error submitting survey response: {str(e)}")
            return {"error": str(e)}
    
    def _analyze_price_sensitivity(self, responses: Dict[str, Any], survey_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze price sensitivity from survey responses"""
        try:
            questions = survey_data["questions"]
            sensitivity_score = 0.0
            willingness_to_pay = Decimal('0')
            total_weight = 0.0
            
            for question in questions:
                question_id = question["question_id"]
                question_type = question["question_type"]
                weight = question["weight"]
                
                if question_id not in responses:
                    continue
                
                response_value = responses[question_id]
                
                if question_type == "scale":
                    # Convert scale responses to sensitivity scores
                    if isinstance(response_value, str) and response_value.startswith(("1", "2", "3", "4", "5")):
                        scale_value = int(response_value[0])
                        # Higher scale values (more likely to buy) = lower sensitivity
                        question_sensitivity = (6 - scale_value) / 5.0
                        sensitivity_score += question_sensitivity * weight
                        total_weight += weight
                
                elif question_type == "price_point":
                    # Direct price point responses
                    try:
                        price_value = Decimal(str(response_value))
                        if price_value > willingness_to_pay:
                            willingness_to_pay = price_value
                    except (ValueError, TypeError):
                        pass
                
                elif question_type == "multiple_choice":
                    # Analyze choice-based responses for sensitivity indicators
                    if "expensive" in response_value.lower():
                        sensitivity_score += 0.8 * weight
                        total_weight += weight
                    elif "cheap" in response_value.lower() or "affordable" in response_value.lower():
                        sensitivity_score += 0.2 * weight
                        total_weight += weight
            
            # Normalize sensitivity score
            if total_weight > 0:
                sensitivity_score = sensitivity_score / total_weight
            
            # Price elasticity estimation (simplified)
            if sensitivity_score > 0:
                price_elasticity = -2.0 * sensitivity_score  # Higher sensitivity = more elastic
            else:
                price_elasticity = -0.5
            
            return {
                "sensitivity_score": round(sensitivity_score, 3),
                "willingness_to_pay": float(willingness_to_pay),
                "price_elasticity": round(price_elasticity, 3),
                "segment": self._classify_price_segment(sensitivity_score),
                "analysis_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing price sensitivity: {str(e)}")
            return {"error": str(e)}
    
    def _classify_price_segment(self, sensitivity_score: float) -> str:
        """Classify user into price sensitivity segment"""
        if sensitivity_score >= 0.7:
            return "highly_price_sensitive"
        elif sensitivity_score >= 0.4:
            return "moderately_price_sensitive"
        else:
            return "low_price_sensitivity"
    
    async def generate_pricing_insights(self) -> Dict[str, Any]:
        """Generate comprehensive pricing insights from all survey responses"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all recent survey responses (last 90 days)
            cursor.execute('''
                SELECT 
                    user_id, survey_type, price_sensitivity_score, willingness_to_pay,
                    questions_responses, submitted_at
                FROM survey_responses 
                WHERE submitted_at >= date('now', '-90 days')
                AND price_sensitivity_score IS NOT NULL
            ''')
            
            responses = cursor.fetchall()
            
            # Get user tier information for segmentation
            cursor.execute('''
                SELECT sr.user_id, bu.tier, sr.price_sensitivity_score, sr.willingness_to_pay
                FROM survey_responses sr
                JOIN beta_users bu ON sr.user_id = bu.id
                WHERE sr.submitted_at >= date('now', '-90 days')
                AND sr.price_sensitivity_score IS NOT NULL
            ''')
            
            user_segments = cursor.fetchall()
            conn.close()
            
            if not responses:
                return {
                    "error": "No survey data available",
                    "message": "Collect more survey responses to generate insights"
                }
            
            # Overall price sensitivity analysis
            sensitivity_scores = [r[2] for r in responses if r[2] is not None]
            wtp_values = [r[3] for r in responses if r[3] is not None and r[3] > 0]
            
            overall_insights = {
                "sample_size": len(responses),
                "avg_sensitivity_score": round(statistics.mean(sensitivity_scores), 3) if sensitivity_scores else 0,
                "sensitivity_distribution": self._calculate_sensitivity_distribution(sensitivity_scores),
                "willingness_to_pay": {
                    "median": round(statistics.median(wtp_values), 2) if wtp_values else 0,
                    "mean": round(statistics.mean(wtp_values), 2) if wtp_values else 0,
                    "percentiles": {
                        "25th": round(statistics.quantiles(wtp_values, n=4)[0], 2) if len(wtp_values) >= 4 else 0,
                        "75th": round(statistics.quantiles(wtp_values, n=4)[2], 2) if len(wtp_values) >= 4 else 0,
                        "90th": round(statistics.quantiles(wtp_values, n=10)[8], 2) if len(wtp_values) >= 10 else 0
                    }
                }
            }
            
            # Segment analysis
            segment_insights = self._analyze_segments_pricing(user_segments)
            
            # Optimal pricing recommendations
            pricing_recommendations = self._generate_pricing_recommendations(
                sensitivity_scores, wtp_values, segment_insights
            )
            
            # Market positioning insights
            market_insights = self._analyze_market_positioning(responses)
            
            return {
                "analysis_date": datetime.now().isoformat(),
                "data_period": "last_90_days",
                "overall_insights": overall_insights,
                "segment_insights": segment_insights,
                "pricing_recommendations": pricing_recommendations,
                "market_insights": market_insights,
                "confidence_level": self._calculate_confidence_level(len(responses))
            }
            
        except Exception as e:
            logger.error(f"Error generating pricing insights: {str(e)}")
            return {"error": str(e)}
    
    def _calculate_sensitivity_distribution(self, scores: List[float]) -> Dict[str, float]:
        """Calculate distribution of price sensitivity"""
        if not scores:
            return {"high": 0, "medium": 0, "low": 0}
        
        high_sensitive = len([s for s in scores if s >= 0.7]) / len(scores)
        medium_sensitive = len([s for s in scores if 0.4 <= s < 0.7]) / len(scores)
        low_sensitive = len([s for s in scores if s < 0.4]) / len(scores)
        
        return {
            "high": round(high_sensitive * 100, 1),
            "medium": round(medium_sensitive * 100, 1),
            "low": round(low_sensitive * 100, 1)
        }
    
    def _analyze_segments_pricing(self, user_segments: List[tuple]) -> Dict[str, Dict[str, Any]]:
        """Analyze pricing by user segments"""
        segment_data = {}
        
        for user_id, tier, sensitivity, wtp in user_segments:
            if tier not in segment_data:
                segment_data[tier] = {
                    "users": [],
                    "sensitivity_scores": [],
                    "wtp_values": []
                }
            
            segment_data[tier]["users"].append(user_id)
            if sensitivity is not None:
                segment_data[tier]["sensitivity_scores"].append(sensitivity)
            if wtp is not None and wtp > 0:
                segment_data[tier]["wtp_values"].append(wtp)
        
        # Calculate statistics for each segment
        segment_insights = {}
        for tier, data in segment_data.items():
            sensitivity_scores = data["sensitivity_scores"]
            wtp_values = data["wtp_values"]
            
            segment_insights[tier] = {
                "user_count": len(data["users"]),
                "avg_sensitivity": round(statistics.mean(sensitivity_scores), 3) if sensitivity_scores else 0,
                "avg_wtp": round(statistics.mean(wtp_values), 2) if wtp_values else 0,
                "median_wtp": round(statistics.median(wtp_values), 2) if wtp_values else 0,
                "price_sensitivity_level": self._classify_price_segment(
                    statistics.mean(sensitivity_scores) if sensitivity_scores else 0.5
                )
            }
        
        return segment_insights
    
    def _generate_pricing_recommendations(
        self, 
        sensitivity_scores: List[float], 
        wtp_values: List[float],
        segment_insights: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate pricing strategy recommendations"""
        recommendations = {
            "optimal_pricing": {},
            "strategies": [],
            "tier_adjustments": {}
        }
        
        if wtp_values:
            median_wtp = statistics.median(wtp_values)
            mean_wtp = statistics.mean(wtp_values)
            
            # Optimal price points based on WTP analysis
            recommendations["optimal_pricing"] = {
                "conservative": round(median_wtp * 0.8, 2),  # 20% below median
                "aggressive": round(mean_wtp * 0.9, 2),      # 10% below mean
                "premium": round(statistics.quantiles(wtp_values, n=4)[2], 2) if len(wtp_values) >= 4 else round(mean_wtp, 2)
            }
        
        # Strategic recommendations based on sensitivity distribution
        if sensitivity_scores:
            avg_sensitivity = statistics.mean(sensitivity_scores)
            
            if avg_sensitivity > 0.6:
                recommendations["strategies"].append({
                    "strategy": "Value-based pricing with clear ROI demonstration",
                    "reason": "High price sensitivity detected"
                })
                recommendations["strategies"].append({
                    "strategy": "Offer multiple tiers with clear value differentiation",
                    "reason": "Price-sensitive users need options"
                })
            elif avg_sensitivity < 0.3:
                recommendations["strategies"].append({
                    "strategy": "Premium positioning with advanced features",
                    "reason": "Low price sensitivity allows higher pricing"
                })
            else:
                recommendations["strategies"].append({
                    "strategy": "Competitive pricing with feature bundling",
                    "reason": "Moderate price sensitivity suggests balanced approach"
                })
        
        # Tier-specific adjustments
        for tier, insights in segment_insights.items():
            if insights["avg_wtp"] > 0:
                recommendations["tier_adjustments"][tier] = {
                    "suggested_price": round(insights["avg_wtp"] * 0.85, 2),
                    "rationale": f"Based on {insights['user_count']} responses with {insights['price_sensitivity_level']} sensitivity"
                }
        
        return recommendations
    
    def _analyze_market_positioning(self, responses: List[tuple]) -> Dict[str, Any]:
        """Analyze market positioning insights from survey data"""
        # This would analyze competitor comparison responses and market positioning
        return {
            "competitive_position": "analysis_requires_competitor_data",
            "differentiation_opportunities": [
                "Focus on unique value proposition",
                "Emphasize ROI and cost savings",
                "Highlight superior support quality"
            ],
            "pricing_confidence": "medium"
        }
    
    def _calculate_confidence_level(self, sample_size: int) -> str:
        """Calculate confidence level based on sample size"""
        if sample_size >= 100:
            return "high"
        elif sample_size >= 30:
            return "medium"
        else:
            return "low"
    
    async def get_survey_completion_rate(self, survey_id: str) -> Dict[str, Any]:
        """Get survey completion statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get survey details and target users
            cursor.execute('''
                SELECT target_users, created_at FROM pricing_surveys WHERE id = ?
            ''', (survey_id,))
            
            survey_info = cursor.fetchone()
            if not survey_info:
                conn.close()
                return {"error": "Survey not found"}
            
            target_users_json, created_at = survey_info
            target_users = json.loads(target_users_json) if target_users_json else []
            
            # Get response count
            cursor.execute('''
                SELECT COUNT(*) FROM survey_responses WHERE survey_id = ?
            ''', (survey_id,))
            
            response_count = cursor.fetchone()[0]
            
            # Get completion rate by day
            cursor.execute('''
                SELECT 
                    DATE(submitted_at) as response_date,
                    COUNT(*) as daily_responses
                FROM survey_responses 
                WHERE survey_id = ?
                GROUP BY DATE(submitted_at)
                ORDER BY response_date
            ''', (survey_id,))
            
            daily_responses = cursor.fetchall()
            conn.close()
            
            # Calculate metrics
            if target_users:
                completion_rate = (response_count / len(target_users)) * 100
            else:
                completion_rate = 0  # Can't calculate without target audience
            
            return {
                "survey_id": survey_id,
                "target_users": len(target_users),
                "total_responses": response_count,
                "completion_rate": round(completion_rate, 2),
                "daily_breakdown": [
                    {"date": date, "responses": count}
                    for date, count in daily_responses
                ],
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting survey completion rate: {str(e)}")
            return {"error": str(e)}

# Global instance
pricing_survey_system = PricingSurveySystem()