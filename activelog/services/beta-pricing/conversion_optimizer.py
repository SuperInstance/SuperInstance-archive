"""
Conversion Rate Optimization System
Analyze and optimize conversion funnels for beta pricing strategies
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
import asyncio

logger = logging.getLogger(__name__)

class FunnelStep(str, Enum):
    LANDING = "landing"
    SIGNUP = "signup"
    ONBOARDING = "onboarding"
    TRIAL = "trial"
    PRICING_PAGE = "pricing_page"
    CHECKOUT = "checkout"
    PAYMENT = "payment"
    ACTIVATION = "activation"

class ConversionEvent(str, Enum):
    PAGE_VIEW = "page_view"
    SIGNUP_START = "signup_start"
    SIGNUP_COMPLETE = "signup_complete"
    TRIAL_START = "trial_start"
    PRICING_VIEW = "pricing_view"
    PLAN_SELECT = "plan_select"
    CHECKOUT_START = "checkout_start"
    PAYMENT_ATTEMPT = "payment_attempt"
    PAYMENT_SUCCESS = "payment_success"
    ACTIVATION_COMPLETE = "activation_complete"

class OptimizationType(str, Enum):
    FUNNEL_STEP = "funnel_step"
    PRICE_POINT = "price_point"
    MESSAGING = "messaging"
    UI_UX = "ui_ux"
    INCENTIVE = "incentive"

@dataclass
class ConversionFunnel:
    funnel_id: str
    name: str
    steps: List[FunnelStep]
    conversion_rates: Dict[str, float]
    drop_off_points: List[str]
    total_conversion_rate: float

@dataclass
class OptimizationExperiment:
    experiment_id: str
    experiment_type: OptimizationType
    target_step: FunnelStep
    baseline_rate: float
    target_improvement: float
    status: str

class ConversionRateOptimizer:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/beta-pricing/data/beta_pricing.db"
        self._initialize_tables()
        
        # Standard conversion funnel steps
        self.default_funnel_steps = [
            FunnelStep.LANDING,
            FunnelStep.SIGNUP,
            FunnelStep.ONBOARDING,
            FunnelStep.TRIAL,
            FunnelStep.PRICING_PAGE,
            FunnelStep.CHECKOUT,
            FunnelStep.PAYMENT,
            FunnelStep.ACTIVATION
        ]
        
        # Benchmark conversion rates (industry averages)
        self.benchmark_rates = {
            FunnelStep.LANDING: 0.15,      # 15% of visitors sign up
            FunnelStep.SIGNUP: 0.80,       # 80% complete signup
            FunnelStep.ONBOARDING: 0.70,   # 70% complete onboarding
            FunnelStep.TRIAL: 0.60,        # 60% start trial
            FunnelStep.PRICING_PAGE: 0.25, # 25% view pricing
            FunnelStep.CHECKOUT: 0.30,     # 30% start checkout
            FunnelStep.PAYMENT: 0.85,      # 85% payment success
            FunnelStep.ACTIVATION: 0.65    # 65% activate after payment
        }
    
    def _initialize_tables(self):
        """Initialize database tables for conversion optimization"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Conversion events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversion_events (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                funnel_step TEXT NOT NULL,
                page_url TEXT,
                price_point DECIMAL,
                experiment_group TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                data TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES beta_users (id)
            )
        ''')
        
        # Conversion funnels table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversion_funnels (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                funnel_steps TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL
            )
        ''')
        
        # Optimization experiments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS optimization_experiments (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                experiment_type TEXT NOT NULL,
                target_step TEXT NOT NULL,
                baseline_rate REAL NOT NULL,
                target_improvement REAL NOT NULL,
                status TEXT DEFAULT 'active',
                start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_date TIMESTAMP,
                results TEXT,
                data TEXT NOT NULL
            )
        ''')
        
        # Conversion insights table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversion_insights (
                id TEXT PRIMARY KEY,
                insight_type TEXT NOT NULL,
                funnel_step TEXT,
                user_segment TEXT,
                insight_description TEXT NOT NULL,
                recommended_action TEXT,
                impact_score REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def track_conversion_event(
        self,
        user_id: str,
        session_id: str,
        event_type: ConversionEvent,
        funnel_step: FunnelStep,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Track a conversion event in the funnel"""
        try:
            event_id = f"CONV_{uuid.uuid4().hex[:8].upper()}"
            
            event_data = {
                "id": event_id,
                "user_id": user_id,
                "session_id": session_id,
                "event_type": event_type.value,
                "funnel_step": funnel_step.value,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat()
            }
            
            # Store event
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO conversion_events 
                (id, user_id, session_id, event_type, funnel_step, page_url,
                 price_point, experiment_group, metadata, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_id, user_id, session_id, event_type.value, funnel_step.value,
                metadata.get("page_url") if metadata else None,
                metadata.get("price_point") if metadata else None,
                metadata.get("experiment_group") if metadata else None,
                json.dumps(metadata or {}),
                json.dumps(event_data)
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Tracked conversion event {event_id}: {event_type.value} at {funnel_step.value}")
            
            return {
                "event_id": event_id,
                "recorded": True,
                "event_type": event_type.value,
                "funnel_step": funnel_step.value
            }
            
        except Exception as e:
            logger.error(f"Error tracking conversion event: {str(e)}")
            return {"error": str(e)}
    
    async def track_conversion(self, user_id: str, conversion_type: str = "signup_to_paid") -> Dict[str, Any]:
        """Track a successful conversion (called from main.py)"""
        try:
            # This is a simplified version for the main API
            return await self.track_conversion_event(
                user_id=user_id,
                session_id=f"SESSION_{uuid.uuid4().hex[:6]}",
                event_type=ConversionEvent.PAYMENT_SUCCESS,
                funnel_step=FunnelStep.PAYMENT,
                metadata={"conversion_type": conversion_type}
            )
        except Exception as e:
            logger.error(f"Error tracking conversion: {str(e)}")
            return {"error": str(e)}
    
    async def analyze_conversion_funnel(
        self,
        period_days: int = 30,
        segment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze conversion funnel performance"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)
            
            # Base query for events in period
            base_query = '''
                SELECT user_id, funnel_step, event_type, timestamp, experiment_group
                FROM conversion_events 
                WHERE timestamp >= ? AND timestamp <= ?
            '''
            
            # Add segment filter if provided
            if segment:
                cursor.execute(base_query + ' AND experiment_group = ?', 
                             (start_date.isoformat(), end_date.isoformat(), segment))
            else:
                cursor.execute(base_query, (start_date.isoformat(), end_date.isoformat()))
            
            events = cursor.fetchall()
            conn.close()
            
            if not events:
                return {
                    "message": "No conversion events found for the specified period",
                    "period_days": period_days
                }
            
            # Organize events by user and step
            user_journeys = {}
            for user_id, step, event_type, timestamp, experiment_group in events:
                if user_id not in user_journeys:
                    user_journeys[user_id] = {
                        "events": [],
                        "experiment_group": experiment_group
                    }
                
                user_journeys[user_id]["events"].append({
                    "step": step,
                    "event_type": event_type,
                    "timestamp": timestamp
                })
            
            # Calculate funnel metrics
            funnel_analysis = self._calculate_funnel_metrics(user_journeys)
            
            # Identify optimization opportunities
            opportunities = self._identify_optimization_opportunities(funnel_analysis)
            
            # Calculate segment performance if applicable
            segment_analysis = self._analyze_segments(user_journeys) if len(user_journeys) > 50 else {}
            
            return {
                "analysis_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": period_days
                },
                "total_users_analyzed": len(user_journeys),
                "funnel_performance": funnel_analysis,
                "optimization_opportunities": opportunities,
                "segment_analysis": segment_analysis,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing conversion funnel: {str(e)}")
            return {"error": str(e)}
    
    def _calculate_funnel_metrics(self, user_journeys: Dict[str, Dict]) -> Dict[str, Any]:
        """Calculate funnel conversion metrics"""
        step_counts = {}
        step_conversions = {}
        
        # Count users at each step
        for user_id, journey in user_journeys.items():
            user_steps = set(event["step"] for event in journey["events"])
            
            for step in self.default_funnel_steps:
                step_value = step.value
                if step_value not in step_counts:
                    step_counts[step_value] = 0
                
                if step_value in user_steps:
                    step_counts[step_value] += 1
        
        # Calculate conversion rates between steps
        funnel_steps = [step.value for step in self.default_funnel_steps]
        
        for i in range(len(funnel_steps) - 1):
            current_step = funnel_steps[i]
            next_step = funnel_steps[i + 1]
            
            current_count = step_counts.get(current_step, 0)
            next_count = step_counts.get(next_step, 0)
            
            if current_count > 0:
                conversion_rate = next_count / current_count
                step_conversions[f"{current_step}_to_{next_step}"] = {
                    "from_step": current_step,
                    "to_step": next_step,
                    "from_count": current_count,
                    "to_count": next_count,
                    "conversion_rate": round(conversion_rate, 4),
                    "benchmark_rate": self.benchmark_rates.get(FunnelStep(next_step), 0.5),
                    "performance": "above" if conversion_rate > self.benchmark_rates.get(FunnelStep(next_step), 0.5) else "below"
                }
        
        # Calculate overall funnel conversion rate
        total_users = len(user_journeys)
        final_step_count = step_counts.get(funnel_steps[-1], 0)
        overall_conversion = final_step_count / total_users if total_users > 0 else 0
        
        return {
            "step_counts": step_counts,
            "step_conversions": step_conversions,
            "overall_conversion_rate": round(overall_conversion, 4),
            "total_users": total_users,
            "funnel_efficiency": round(overall_conversion / 0.01, 2) if overall_conversion > 0 else 0  # Efficiency score out of 100
        }
    
    def _identify_optimization_opportunities(self, funnel_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify optimization opportunities in the funnel"""
        opportunities = []
        step_conversions = funnel_analysis.get("step_conversions", {})
        
        for conversion_key, conversion_data in step_conversions.items():
            conversion_rate = conversion_data["conversion_rate"]
            benchmark_rate = conversion_data["benchmark_rate"]
            from_step = conversion_data["from_step"]
            to_step = conversion_data["to_step"]
            
            # Identify underperforming steps
            if conversion_rate < benchmark_rate * 0.8:  # 20% below benchmark
                impact_score = (benchmark_rate - conversion_rate) * conversion_data["from_count"]
                
                opportunities.append({
                    "type": "underperforming_step",
                    "from_step": from_step,
                    "to_step": to_step,
                    "current_rate": conversion_rate,
                    "benchmark_rate": benchmark_rate,
                    "potential_improvement": round((benchmark_rate - conversion_rate) * 100, 2),
                    "impact_score": round(impact_score, 2),
                    "recommended_actions": self._get_step_optimization_recommendations(from_step, to_step)
                })
        
        # Identify drop-off points
        largest_drop_off = max(step_conversions.items(), 
                             key=lambda x: x[1]["from_count"] - x[1]["to_count"])
        
        if largest_drop_off:
            drop_off_data = largest_drop_off[1]
            drop_off_count = drop_off_data["from_count"] - drop_off_data["to_count"]
            
            opportunities.append({
                "type": "major_drop_off",
                "from_step": drop_off_data["from_step"],
                "to_step": drop_off_data["to_step"],
                "drop_off_count": drop_off_count,
                "drop_off_rate": round((1 - drop_off_data["conversion_rate"]) * 100, 2),
                "potential_recovery": round(drop_off_count * 0.3, 0),  # Assume 30% recovery possible
                "recommended_actions": ["Analyze user feedback", "Improve UX", "Add exit intent surveys"]
            })
        
        # Sort by impact score
        opportunities.sort(key=lambda x: x.get("impact_score", 0), reverse=True)
        
        return opportunities
    
    def _get_step_optimization_recommendations(self, from_step: str, to_step: str) -> List[str]:
        """Get specific optimization recommendations for step transitions"""
        recommendations = {
            "landing_to_signup": [
                "Optimize value proposition messaging",
                "Reduce signup friction",
                "Add social proof elements",
                "A/B test CTA buttons"
            ],
            "signup_to_onboarding": [
                "Simplify signup form",
                "Reduce required fields",
                "Add progress indicators",
                "Email verification optimization"
            ],
            "trial_to_pricing_page": [
                "Improve trial experience",
                "Add usage limit notifications",
                "Show pricing before trial ends",
                "Highlight value during trial"
            ],
            "pricing_page_to_checkout": [
                "Optimize pricing presentation",
                "Add feature comparisons",
                "Include testimonials",
                "Offer limited-time discounts"
            ],
            "checkout_to_payment": [
                "Reduce checkout steps",
                "Add payment security badges",
                "Offer multiple payment options",
                "Display money-back guarantee"
            ]
        }
        
        transition_key = f"{from_step}_to_{to_step}"
        return recommendations.get(transition_key, ["Analyze user behavior", "A/B test improvements"])
    
    def _analyze_segments(self, user_journeys: Dict[str, Dict]) -> Dict[str, Any]:
        """Analyze conversion performance by segments"""
        segment_performance = {}
        
        # Group users by experiment group
        segments = {}
        for user_id, journey in user_journeys.items():
            experiment_group = journey.get("experiment_group", "unknown")
            if experiment_group not in segments:
                segments[experiment_group] = []
            segments[experiment_group].append(journey["events"])
        
        # Calculate performance for each segment
        for segment, journeys in segments.items():
            if len(journeys) < 10:  # Skip small segments
                continue
            
            # Calculate segment funnel metrics
            segment_step_counts = {}
            for journey in journeys:
                journey_steps = set(event["step"] for event in journey)
                for step in self.default_funnel_steps:
                    step_value = step.value
                    if step_value not in segment_step_counts:
                        segment_step_counts[step_value] = 0
                    if step_value in journey_steps:
                        segment_step_counts[step_value] += 1
            
            # Calculate overall conversion for segment
            total_users = len(journeys)
            final_step = self.default_funnel_steps[-1].value
            final_conversions = segment_step_counts.get(final_step, 0)
            segment_conversion_rate = final_conversions / total_users if total_users > 0 else 0
            
            segment_performance[segment] = {
                "user_count": total_users,
                "conversion_rate": round(segment_conversion_rate, 4),
                "step_counts": segment_step_counts
            }
        
        return segment_performance
    
    async def get_conversion_analytics(
        self, 
        period: str = "month", 
        segment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get conversion rate analytics (called from main.py)"""
        try:
            # Convert period to days
            period_days = {
                "week": 7,
                "month": 30,
                "quarter": 90
            }.get(period, 30)
            
            return await self.analyze_conversion_funnel(period_days, segment)
            
        except Exception as e:
            logger.error(f"Error getting conversion analytics: {str(e)}")
            return {"error": str(e)}
    
    async def optimize_funnel(
        self,
        funnel_step: str,
        target_metric: str = "conversion_rate"
    ) -> Dict[str, Any]:
        """Optimize specific funnel step (called from main.py)"""
        try:
            # Get current performance for the step
            funnel_analysis = await self.analyze_conversion_funnel()
            
            if "error" in funnel_analysis:
                return funnel_analysis
            
            step_conversions = funnel_analysis.get("funnel_performance", {}).get("step_conversions", {})
            
            # Find relevant conversion data for the step
            relevant_conversions = {
                k: v for k, v in step_conversions.items()
                if funnel_step in k
            }
            
            if not relevant_conversions:
                return {"error": f"No conversion data found for step: {funnel_step}"}
            
            # Generate optimization recommendations
            recommendations = []
            for conv_key, conv_data in relevant_conversions.items():
                if conv_data["performance"] == "below":
                    recommendations.extend(
                        self._get_step_optimization_recommendations(
                            conv_data["from_step"], 
                            conv_data["to_step"]
                        )
                    )
            
            # Create optimization experiment
            experiment = await self._create_optimization_experiment(
                funnel_step, target_metric, relevant_conversions
            )
            
            return {
                "funnel_step": funnel_step,
                "target_metric": target_metric,
                "current_performance": relevant_conversions,
                "optimization_recommendations": recommendations,
                "experiment_created": experiment
            }
            
        except Exception as e:
            logger.error(f"Error optimizing funnel: {str(e)}")
            return {"error": str(e)}
    
    async def _create_optimization_experiment(
        self,
        funnel_step: str,
        target_metric: str,
        current_performance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create an optimization experiment"""
        try:
            experiment_id = f"OPT_{uuid.uuid4().hex[:8].upper()}"
            
            # Calculate baseline rate
            baseline_rates = [data["conversion_rate"] for data in current_performance.values()]
            baseline_rate = statistics.mean(baseline_rates) if baseline_rates else 0
            
            # Set target improvement (aim for 20% relative improvement)
            target_improvement = 0.20
            
            experiment_data = {
                "id": experiment_id,
                "name": f"Optimize {funnel_step} conversion",
                "experiment_type": OptimizationType.FUNNEL_STEP.value,
                "target_step": funnel_step,
                "baseline_rate": baseline_rate,
                "target_improvement": target_improvement,
                "target_rate": baseline_rate * (1 + target_improvement),
                "created_at": datetime.now().isoformat()
            }
            
            # Store experiment
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO optimization_experiments 
                (id, name, experiment_type, target_step, baseline_rate, target_improvement, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                experiment_id, experiment_data["name"], experiment_data["experiment_type"],
                funnel_step, baseline_rate, target_improvement,
                json.dumps(experiment_data)
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Created optimization experiment {experiment_id}")
            
            return experiment_data
            
        except Exception as e:
            logger.error(f"Error creating optimization experiment: {str(e)}")
            return {"error": str(e)}
    
    async def get_conversion_summary(self) -> Dict[str, Any]:
        """Get conversion summary (called from main.py)"""
        try:
            # Get recent funnel analysis
            funnel_analysis = await self.analyze_conversion_funnel(30)  # Last 30 days
            
            if "error" in funnel_analysis:
                return {"summary": "No conversion data available"}
            
            funnel_perf = funnel_analysis.get("funnel_performance", {})
            
            return {
                "period": "last_30_days",
                "total_users": funnel_perf.get("total_users", 0),
                "overall_conversion_rate": funnel_perf.get("overall_conversion_rate", 0),
                "funnel_efficiency": funnel_perf.get("funnel_efficiency", 0),
                "key_opportunities": len(funnel_analysis.get("optimization_opportunities", [])),
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting conversion summary: {str(e)}")
            return {"error": str(e)}
    
    async def create_conversion_insight(
        self,
        insight_type: str,
        funnel_step: Optional[str],
        description: str,
        recommended_action: str,
        impact_score: float = 0.5
    ) -> Dict[str, Any]:
        """Create and store a conversion insight"""
        try:
            insight_id = f"INSIGHT_{uuid.uuid4().hex[:8].upper()}"
            
            insight_data = {
                "id": insight_id,
                "insight_type": insight_type,
                "funnel_step": funnel_step,
                "description": description,
                "recommended_action": recommended_action,
                "impact_score": impact_score,
                "created_at": datetime.now().isoformat()
            }
            
            # Store insight
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO conversion_insights 
                (id, insight_type, funnel_step, insight_description, recommended_action, impact_score, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                insight_id, insight_type, funnel_step, description,
                recommended_action, impact_score, json.dumps(insight_data)
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Created conversion insight {insight_id}")
            
            return insight_data
            
        except Exception as e:
            logger.error(f"Error creating conversion insight: {str(e)}")
            return {"error": str(e)}

# Global instance
conversion_rate_optimizer = ConversionRateOptimizer()