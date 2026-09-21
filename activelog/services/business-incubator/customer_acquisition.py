#!/usr/bin/env python3
"""
Customer Acquisition Tracking System
Comprehensive customer acquisition and growth management

Features:
- Multi-channel acquisition tracking
- Customer lifecycle management
- Attribution modeling and analytics
- A/B testing for acquisition campaigns
- Referral program management
- Lead scoring and qualification
- Conversion funnel optimization
- Customer onboarding tracking
- Churn prediction and prevention
- Lifetime value (LTV) calculation
- Customer acquisition cost (CAC) optimization
- Cohort analysis and retention tracking
- Marketing automation workflows
- Social media acquisition campaigns
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

class AcquisitionChannel(str, Enum):
    ORGANIC_SEARCH = "organic_search"
    PAID_SEARCH = "paid_search"
    SOCIAL_MEDIA = "social_media"
    EMAIL_MARKETING = "email_marketing"
    CONTENT_MARKETING = "content_marketing"
    REFERRAL = "referral"
    DIRECT = "direct"
    AFFILIATE = "affiliate"
    DISPLAY_ADS = "display_ads"
    PR_MEDIA = "pr_media"
    EVENTS = "events"
    PARTNERSHIPS = "partnerships"

class CustomerStage(str, Enum):
    VISITOR = "visitor"
    LEAD = "lead"
    QUALIFIED_LEAD = "qualified_lead"
    TRIAL = "trial"
    CUSTOMER = "customer"
    ADVOCATE = "advocate"
    CHURNED = "churned"

class CampaignType(str, Enum):
    AWARENESS = "awareness"
    CONSIDERATION = "consideration"
    CONVERSION = "conversion"
    RETENTION = "retention"
    REFERRAL = "referral"

class CustomerRecord(BaseModel):
    id: str
    business_id: str
    
    # Identity
    email: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    
    # Acquisition data
    acquisition_channel: AcquisitionChannel
    acquisition_campaign: Optional[str] = None
    acquisition_date: datetime
    referrer: Optional[str] = None
    landing_page: Optional[str] = None
    
    # Journey tracking
    current_stage: CustomerStage = CustomerStage.VISITOR
    stage_history: List[Dict[str, Any]] = []
    touchpoints: List[Dict[str, Any]] = []
    
    # Scoring
    lead_score: int = 0
    engagement_score: float = 0.0
    likelihood_to_convert: float = 0.0
    
    # Value metrics
    total_spent: float = 0.0
    lifetime_value: float = 0.0
    predicted_ltv: float = 0.0
    
    # Behavior
    website_visits: int = 0
    email_opens: int = 0
    email_clicks: int = 0
    content_downloads: int = 0
    demo_requests: int = 0
    
    # Status
    is_active: bool = True
    churn_risk_score: float = 0.0
    last_activity: datetime
    
    created_at: datetime
    updated_at: datetime

class Campaign(BaseModel):
    id: str
    business_id: str
    name: str
    description: str
    
    # Campaign details
    type: CampaignType
    channel: AcquisitionChannel
    start_date: datetime
    end_date: Optional[datetime] = None
    
    # Budget and spend
    budget: float
    spend: float = 0.0
    cost_per_click: Optional[float] = None
    cost_per_acquisition: Optional[float] = None
    
    # Targeting
    target_audience: Dict[str, Any] = {}
    geographic_targeting: List[str] = []
    demographic_targeting: Dict[str, Any] = {}
    
    # Creative assets
    creative_assets: List[str] = []
    messaging: Dict[str, str] = {}
    
    # Performance metrics
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    click_through_rate: float = 0.0
    conversion_rate: float = 0.0
    
    # Results
    leads_generated: int = 0
    customers_acquired: int = 0
    revenue_generated: float = 0.0
    
    # Status
    is_active: bool = True
    
    created_at: datetime
    updated_at: datetime
    created_by: str

class Funnel(BaseModel):
    id: str
    business_id: str
    name: str
    description: str
    
    # Funnel stages
    stages: List[Dict[str, Any]]  # [{"name": "awareness", "conversion_rate": 0.1}]
    
    # Metrics by stage
    stage_metrics: Dict[str, Dict[str, int]] = {}  # stage_name -> metrics
    
    # Conversion rates
    overall_conversion_rate: float = 0.0
    stage_conversion_rates: Dict[str, float] = {}
    
    # Optimization
    bottlenecks: List[str] = []
    optimization_opportunities: List[Dict[str, Any]] = []
    
    created_at: datetime
    updated_at: datetime

class ReferralProgram(BaseModel):
    id: str
    business_id: str
    name: str
    description: str
    
    # Program structure
    reward_type: str  # cash, credit, discount, product
    referrer_reward: float
    referee_reward: float
    
    # Rules
    minimum_requirements: Dict[str, Any] = {}
    expiration_days: Optional[int] = None
    max_referrals_per_user: Optional[int] = None
    
    # Tracking
    total_referrals: int = 0
    successful_referrals: int = 0
    total_rewards_paid: float = 0.0
    
    # Performance
    conversion_rate: float = 0.0
    average_referee_value: float = 0.0
    program_roi: float = 0.0
    
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

class Cohort(BaseModel):
    id: str
    business_id: str
    name: str
    
    # Cohort definition
    cohort_date: datetime  # Usually month/quarter
    acquisition_channel: Optional[AcquisitionChannel] = None
    campaign_id: Optional[str] = None
    
    # Size
    initial_size: int
    current_size: int
    
    # Retention by period (weeks/months)
    retention_rates: Dict[str, float] = {}  # "week_1": 0.85, "month_1": 0.70
    
    # Revenue metrics
    revenue_by_period: Dict[str, float] = {}
    cumulative_revenue: float = 0.0
    average_revenue_per_user: float = 0.0
    
    created_at: datetime
    updated_at: datetime

class CustomerAcquisitionManager:
    def __init__(self):
        self.customers: Dict[str, CustomerRecord] = {}
        self.campaigns: Dict[str, Campaign] = {}
        self.funnels: Dict[str, Funnel] = {}
        self.referral_programs: Dict[str, ReferralProgram] = {}
        self.cohorts: Dict[str, Cohort] = {}
        
        # Analytics cache
        self.acquisition_analytics: Dict[str, Dict[str, Any]] = {}
        
        # Initialize default funnel
        self._initialize_default_funnel()
    
    def _initialize_default_funnel(self):
        """Initialize a default acquisition funnel"""
        default_funnel = Funnel(
            id=str(uuid.uuid4()),
            business_id="default",
            name="Standard Acquisition Funnel",
            description="Default customer acquisition funnel",
            stages=[
                {"name": "awareness", "description": "Initial awareness", "order": 1},
                {"name": "interest", "description": "Showed interest", "order": 2},
                {"name": "consideration", "description": "Considering purchase", "order": 3},
                {"name": "trial", "description": "Started trial", "order": 4},
                {"name": "purchase", "description": "Made purchase", "order": 5},
                {"name": "advocacy", "description": "Became advocate", "order": 6}
            ],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.funnels[default_funnel.id] = default_funnel
    
    async def track_customer(
        self, 
        business_id: str, 
        customer_data: Dict[str, Any], 
        acquisition_data: Dict[str, Any]
    ) -> CustomerRecord:
        """Track a new customer acquisition"""
        
        customer_id = customer_data.get("id", str(uuid.uuid4()))
        
        # Check if customer already exists
        existing_customer = None
        if customer_data.get("email"):
            existing_customer = self._find_customer_by_email(business_id, customer_data["email"])
        
        if existing_customer:
            # Update existing customer with new touchpoint
            await self._add_touchpoint(existing_customer.id, acquisition_data)
            return existing_customer
        
        # Create new customer record
        customer = CustomerRecord(
            id=customer_id,
            business_id=business_id,
            email=customer_data.get("email"),
            name=customer_data.get("name"),
            phone=customer_data.get("phone"),
            acquisition_channel=AcquisitionChannel(acquisition_data.get("channel", "direct")),
            acquisition_campaign=acquisition_data.get("campaign"),
            acquisition_date=datetime.now(),
            referrer=acquisition_data.get("referrer"),
            landing_page=acquisition_data.get("landing_page"),
            current_stage=CustomerStage.VISITOR,
            last_activity=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Add initial stage to history
        customer.stage_history.append({
            "stage": CustomerStage.VISITOR,
            "timestamp": datetime.now().isoformat(),
            "source": "acquisition"
        })
        
        # Add initial touchpoint
        customer.touchpoints.append({
            "id": str(uuid.uuid4()),
            "type": "acquisition",
            "channel": customer.acquisition_channel,
            "campaign": customer.acquisition_campaign,
            "timestamp": datetime.now().isoformat(),
            "data": acquisition_data
        })
        
        self.customers[customer_id] = customer
        
        # Update campaign metrics if applicable
        if acquisition_data.get("campaign"):
            await self._update_campaign_metrics(acquisition_data["campaign"], "lead")
        
        return customer
    
    def _find_customer_by_email(self, business_id: str, email: str) -> Optional[CustomerRecord]:
        """Find customer by email address"""
        for customer in self.customers.values():
            if customer.business_id == business_id and customer.email == email:
                return customer
        return None
    
    async def _add_touchpoint(self, customer_id: str, touchpoint_data: Dict[str, Any]):
        """Add a new touchpoint to customer journey"""
        customer = self.customers.get(customer_id)
        if not customer:
            return
        
        touchpoint = {
            "id": str(uuid.uuid4()),
            "type": touchpoint_data.get("type", "interaction"),
            "channel": touchpoint_data.get("channel"),
            "campaign": touchpoint_data.get("campaign"),
            "timestamp": datetime.now().isoformat(),
            "data": touchpoint_data
        }
        
        customer.touchpoints.append(touchpoint)
        customer.last_activity = datetime.now()
        customer.updated_at = datetime.now()
        
        # Update engagement score
        customer.engagement_score += touchpoint_data.get("engagement_value", 1.0)
    
    async def update_customer_stage(self, customer_id: str, new_stage: CustomerStage, context: Dict[str, Any] = {}) -> bool:
        """Update customer to new stage in acquisition funnel"""
        customer = self.customers.get(customer_id)
        if not customer:
            return False
        
        old_stage = customer.current_stage
        customer.current_stage = new_stage
        customer.updated_at = datetime.now()
        customer.last_activity = datetime.now()
        
        # Add to stage history
        customer.stage_history.append({
            "stage": new_stage,
            "previous_stage": old_stage,
            "timestamp": datetime.now().isoformat(),
            "context": context
        })
        
        # Update lead score based on progression
        stage_scores = {
            CustomerStage.VISITOR: 10,
            CustomerStage.LEAD: 25,
            CustomerStage.QUALIFIED_LEAD: 50,
            CustomerStage.TRIAL: 75,
            CustomerStage.CUSTOMER: 100,
            CustomerStage.ADVOCATE: 120
        }
        customer.lead_score = stage_scores.get(new_stage, customer.lead_score)
        
        # Update likelihood to convert
        customer.likelihood_to_convert = self._calculate_conversion_likelihood(customer)
        
        # Update campaign metrics if customer converted
        if new_stage == CustomerStage.CUSTOMER and customer.acquisition_campaign:
            await self._update_campaign_metrics(customer.acquisition_campaign, "conversion")
        
        return True
    
    def _calculate_conversion_likelihood(self, customer: CustomerRecord) -> float:
        """Calculate likelihood of customer to convert"""
        # Simplified scoring model
        score = 0.0
        
        # Stage progression score
        stage_weights = {
            CustomerStage.VISITOR: 0.1,
            CustomerStage.LEAD: 0.2,
            CustomerStage.QUALIFIED_LEAD: 0.5,
            CustomerStage.TRIAL: 0.8,
            CustomerStage.CUSTOMER: 1.0,
            CustomerStage.ADVOCATE: 1.0
        }
        score += stage_weights.get(customer.current_stage, 0.0) * 40
        
        # Engagement score
        score += min(customer.engagement_score / 10, 1.0) * 30
        
        # Activity recency (last 30 days = full score)
        days_since_activity = (datetime.now() - customer.last_activity).days
        recency_score = max(0, 1 - (days_since_activity / 30)) * 20
        score += recency_score
        
        # Touchpoint quantity
        touchpoint_score = min(len(customer.touchpoints) / 5, 1.0) * 10
        score += touchpoint_score
        
        return min(score / 100, 1.0)
    
    async def create_campaign(self, business_id: str, campaign_data: Dict[str, Any]) -> Campaign:
        """Create a new acquisition campaign"""
        
        campaign_id = str(uuid.uuid4())
        
        campaign = Campaign(
            id=campaign_id,
            business_id=business_id,
            name=campaign_data["name"],
            description=campaign_data.get("description", ""),
            type=CampaignType(campaign_data.get("type", "awareness")),
            channel=AcquisitionChannel(campaign_data.get("channel", "organic_search")),
            start_date=campaign_data.get("start_date", datetime.now()),
            end_date=campaign_data.get("end_date"),
            budget=campaign_data.get("budget", 0.0),
            target_audience=campaign_data.get("target_audience", {}),
            geographic_targeting=campaign_data.get("geographic_targeting", []),
            demographic_targeting=campaign_data.get("demographic_targeting", {}),
            creative_assets=campaign_data.get("creative_assets", []),
            messaging=campaign_data.get("messaging", {}),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            created_by=campaign_data.get("created_by", "user")
        )
        
        self.campaigns[campaign_id] = campaign
        return campaign
    
    async def _update_campaign_metrics(self, campaign_id: str, metric_type: str):
        """Update campaign performance metrics"""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return
        
        if metric_type == "impression":
            campaign.impressions += 1
        elif metric_type == "click":
            campaign.clicks += 1
            campaign.click_through_rate = (campaign.clicks / campaign.impressions) if campaign.impressions > 0 else 0
        elif metric_type == "lead":
            campaign.leads_generated += 1
        elif metric_type == "conversion":
            campaign.conversions += 1
            campaign.customers_acquired += 1
            campaign.conversion_rate = (campaign.conversions / campaign.clicks) if campaign.clicks > 0 else 0
        
        campaign.updated_at = datetime.now()
    
    async def calculate_customer_acquisition_cost(self, business_id: str, channel: Optional[AcquisitionChannel] = None, period_days: int = 30) -> Dict[str, Any]:
        """Calculate Customer Acquisition Cost (CAC) by channel"""
        
        # Get campaigns in period
        start_date = datetime.now() - timedelta(days=period_days)
        relevant_campaigns = [
            c for c in self.campaigns.values() 
            if c.business_id == business_id and c.start_date >= start_date
        ]
        
        if channel:
            relevant_campaigns = [c for c in relevant_campaigns if c.channel == channel]
        
        # Calculate total spend and acquisitions
        total_spend = sum(c.spend for c in relevant_campaigns)
        total_acquisitions = sum(c.customers_acquired for c in relevant_campaigns)
        
        # Calculate CAC by channel
        cac_by_channel = {}
        for ch in AcquisitionChannel:
            channel_campaigns = [c for c in relevant_campaigns if c.channel == ch]
            channel_spend = sum(c.spend for c in channel_campaigns)
            channel_acquisitions = sum(c.customers_acquired for c in channel_campaigns)
            
            if channel_acquisitions > 0:
                cac_by_channel[ch.value] = channel_spend / channel_acquisitions
            else:
                cac_by_channel[ch.value] = 0
        
        # Overall CAC
        overall_cac = total_spend / total_acquisitions if total_acquisitions > 0 else 0
        
        return {
            "overall_cac": overall_cac,
            "cac_by_channel": cac_by_channel,
            "total_spend": total_spend,
            "total_acquisitions": total_acquisitions,
            "period_days": period_days,
            "analysis_date": datetime.now().isoformat()
        }
    
    async def calculate_lifetime_value(self, business_id: str, segment: Optional[str] = None) -> Dict[str, Any]:
        """Calculate Customer Lifetime Value (LTV)"""
        
        # Get customers for analysis
        customers = [c for c in self.customers.values() if c.business_id == business_id]
        if segment:
            # Filter by segment (could be channel, campaign, etc.)
            customers = [c for c in customers if c.acquisition_channel.value == segment]
        
        paying_customers = [c for c in customers if c.current_stage in [CustomerStage.CUSTOMER, CustomerStage.ADVOCATE]]
        
        if not paying_customers:
            return {"ltv": 0, "customer_count": 0, "error": "No paying customers found"}
        
        # Calculate average revenue per customer
        total_revenue = sum(c.total_spent for c in paying_customers)
        average_revenue = total_revenue / len(paying_customers)
        
        # Calculate average customer lifespan (simplified)
        lifespans = []
        for customer in paying_customers:
            if customer.current_stage == CustomerStage.CHURNED:
                # Calculate actual lifespan
                first_purchase = None
                last_activity = customer.last_activity
                
                for stage in customer.stage_history:
                    if stage["stage"] == CustomerStage.CUSTOMER:
                        first_purchase = datetime.fromisoformat(stage["timestamp"].replace('Z', '+00:00'))
                        break
                
                if first_purchase:
                    lifespan_days = (last_activity - first_purchase).days
                    lifespans.append(lifespan_days)
            else:
                # For active customers, estimate based on time since acquisition
                days_active = (datetime.now() - customer.acquisition_date).days
                lifespans.append(days_active)
        
        average_lifespan_days = statistics.mean(lifespans) if lifespans else 365
        
        # Calculate purchase frequency (simplified)
        total_purchases = sum(1 for c in paying_customers if c.total_spent > 0)
        purchase_frequency = total_purchases / len(paying_customers) if paying_customers else 1
        
        # LTV Calculation: Average Order Value × Purchase Frequency × Customer Lifespan
        ltv = average_revenue * purchase_frequency * (average_lifespan_days / 365)
        
        # Calculate by channel
        ltv_by_channel = {}
        for channel in AcquisitionChannel:
            channel_customers = [c for c in paying_customers if c.acquisition_channel == channel]
            if channel_customers:
                channel_revenue = sum(c.total_spent for c in channel_customers)
                channel_avg_revenue = channel_revenue / len(channel_customers)
                ltv_by_channel[channel.value] = channel_avg_revenue * purchase_frequency * (average_lifespan_days / 365)
        
        return {
            "overall_ltv": round(ltv, 2),
            "ltv_by_channel": {k: round(v, 2) for k, v in ltv_by_channel.items()},
            "average_revenue_per_customer": round(average_revenue, 2),
            "average_lifespan_days": round(average_lifespan_days, 1),
            "purchase_frequency": round(purchase_frequency, 2),
            "paying_customers": len(paying_customers),
            "total_customers": len(customers)
        }
    
    async def create_cohort_analysis(self, business_id: str, period: str = "monthly") -> List[Cohort]:
        """Create cohort analysis for customer retention"""
        
        customers = [c for c in self.customers.values() if c.business_id == business_id]
        
        # Group customers by acquisition period
        cohorts_data = {}
        
        for customer in customers:
            if period == "monthly":
                cohort_key = customer.acquisition_date.strftime("%Y-%m")
            elif period == "weekly":
                cohort_key = customer.acquisition_date.strftime("%Y-W%W")
            else:  # daily
                cohort_key = customer.acquisition_date.strftime("%Y-%m-%d")
            
            if cohort_key not in cohorts_data:
                cohorts_data[cohort_key] = []
            cohorts_data[cohort_key].append(customer)
        
        cohorts = []
        
        for cohort_period, cohort_customers in cohorts_data.items():
            cohort_id = str(uuid.uuid4())
            
            # Calculate retention rates
            retention_rates = {}
            total_customers = len(cohort_customers)
            
            # Calculate retention for different periods
            for weeks in [1, 4, 12, 24, 52]:  # 1 week, 1 month, 3 months, 6 months, 1 year
                cutoff_date = cohort_customers[0].acquisition_date + timedelta(weeks=weeks)
                if cutoff_date <= datetime.now():
                    active_customers = len([
                        c for c in cohort_customers 
                        if c.last_activity >= cutoff_date and c.current_stage != CustomerStage.CHURNED
                    ])
                    retention_rates[f"week_{weeks}"] = (active_customers / total_customers) if total_customers > 0 else 0
            
            # Calculate revenue metrics
            revenue_by_period = {}
            cumulative_revenue = sum(c.total_spent for c in cohort_customers)
            
            cohort = Cohort(
                id=cohort_id,
                business_id=business_id,
                name=f"Cohort {cohort_period}",
                cohort_date=cohort_customers[0].acquisition_date,
                initial_size=total_customers,
                current_size=len([c for c in cohort_customers if c.current_stage != CustomerStage.CHURNED]),
                retention_rates=retention_rates,
                revenue_by_period=revenue_by_period,
                cumulative_revenue=cumulative_revenue,
                average_revenue_per_user=cumulative_revenue / total_customers if total_customers > 0 else 0,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            cohorts.append(cohort)
            self.cohorts[cohort_id] = cohort
        
        return sorted(cohorts, key=lambda x: x.cohort_date, reverse=True)
    
    async def create_referral_program(self, business_id: str, program_data: Dict[str, Any]) -> ReferralProgram:
        """Create a new referral program"""
        
        program_id = str(uuid.uuid4())
        
        program = ReferralProgram(
            id=program_id,
            business_id=business_id,
            name=program_data["name"],
            description=program_data.get("description", ""),
            reward_type=program_data.get("reward_type", "credit"),
            referrer_reward=program_data.get("referrer_reward", 10.0),
            referee_reward=program_data.get("referee_reward", 5.0),
            minimum_requirements=program_data.get("minimum_requirements", {}),
            expiration_days=program_data.get("expiration_days"),
            max_referrals_per_user=program_data.get("max_referrals_per_user"),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.referral_programs[program_id] = program
        return program
    
    async def process_referral(self, program_id: str, referrer_id: str, referee_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a referral through a referral program"""
        
        program = self.referral_programs.get(program_id)
        referrer = self.customers.get(referrer_id)
        
        if not program or not referrer:
            return {"success": False, "error": "Program or referrer not found"}
        
        # Track the referred customer
        referee_acquisition_data = {
            "channel": "referral",
            "campaign": f"referral_program_{program_id}",
            "referrer": referrer_id,
            "landing_page": referee_data.get("landing_page")
        }
        
        referee = await self.track_customer(
            business_id=program.business_id,
            customer_data=referee_data,
            acquisition_data=referee_acquisition_data
        )
        
        # Update program metrics
        program.total_referrals += 1
        
        # Check if referral converts (for now, assume immediate conversion)
        # In practice, this would be checked when the referee actually converts
        if referee_data.get("converts", False):
            program.successful_referrals += 1
            program.total_rewards_paid += (program.referrer_reward + program.referee_reward)
            
            # Update program performance metrics
            program.conversion_rate = program.successful_referrals / program.total_referrals
            program.average_referee_value = referee_data.get("value", 0.0)
        
        program.updated_at = datetime.now()
        
        return {
            "success": True,
            "referral_id": str(uuid.uuid4()),
            "referee_id": referee.id,
            "referrer_reward": program.referrer_reward,
            "referee_reward": program.referee_reward
        }
    
    async def analyze_funnel_performance(self, business_id: str, funnel_id: Optional[str] = None) -> Dict[str, Any]:
        """Analyze customer acquisition funnel performance"""
        
        # Get relevant customers
        customers = [c for c in self.customers.values() if c.business_id == business_id]
        
        # Count customers by stage
        stage_counts = {}
        for stage in CustomerStage:
            stage_counts[stage.value] = len([c for c in customers if c.current_stage == stage])
        
        # Calculate conversion rates between stages
        stage_order = [
            CustomerStage.VISITOR,
            CustomerStage.LEAD, 
            CustomerStage.QUALIFIED_LEAD,
            CustomerStage.TRIAL,
            CustomerStage.CUSTOMER,
            CustomerStage.ADVOCATE
        ]
        
        conversion_rates = {}
        for i in range(len(stage_order) - 1):
            current_stage = stage_order[i]
            next_stage = stage_order[i + 1]
            
            current_count = stage_counts.get(current_stage.value, 0)
            next_count = stage_counts.get(next_stage.value, 0)
            
            # Add customers from further stages (they passed through this conversion)
            for j in range(i + 2, len(stage_order)):
                next_count += stage_counts.get(stage_order[j].value, 0)
            
            conversion_rate = (next_count / current_count) if current_count > 0 else 0
            conversion_rates[f"{current_stage.value}_to_{next_stage.value}"] = conversion_rate
        
        # Identify bottlenecks (lowest conversion rates)
        bottlenecks = sorted(conversion_rates.items(), key=lambda x: x[1])[:3]
        
        # Calculate overall funnel metrics
        total_visitors = stage_counts.get(CustomerStage.VISITOR.value, 0) + len([
            c for c in customers if c.current_stage != CustomerStage.VISITOR
        ])
        total_customers = stage_counts.get(CustomerStage.CUSTOMER.value, 0) + stage_counts.get(CustomerStage.ADVOCATE.value, 0)
        
        overall_conversion_rate = (total_customers / total_visitors) if total_visitors > 0 else 0
        
        return {
            "business_id": business_id,
            "stage_counts": stage_counts,
            "conversion_rates": conversion_rates,
            "overall_conversion_rate": overall_conversion_rate,
            "bottlenecks": [{"stage_transition": b[0], "conversion_rate": b[1]} for b in bottlenecks],
            "total_visitors": total_visitors,
            "total_customers": total_customers,
            "analysis_date": datetime.now().isoformat(),
            "recommendations": self._generate_funnel_recommendations(conversion_rates, bottlenecks)
        }
    
    def _generate_funnel_recommendations(self, conversion_rates: Dict[str, float], bottlenecks: List[Tuple[str, float]]) -> List[str]:
        """Generate recommendations based on funnel analysis"""
        recommendations = []
        
        for bottleneck in bottlenecks[:2]:  # Top 2 bottlenecks
            stage_transition, rate = bottleneck
            
            if rate < 0.1:  # Less than 10% conversion
                recommendations.append(f"Critical bottleneck at {stage_transition}: Only {rate:.1%} conversion rate. Consider A/B testing different approaches.")
            elif rate < 0.3:  # Less than 30% conversion
                recommendations.append(f"Optimization opportunity at {stage_transition}: {rate:.1%} conversion rate can be improved with better messaging or incentives.")
        
        # General recommendations
        if conversion_rates.get("visitor_to_lead", 0) < 0.02:
            recommendations.append("Low visitor-to-lead conversion suggests weak value proposition or targeting issues.")
        
        if conversion_rates.get("trial_to_customer", 0) < 0.2:
            recommendations.append("Low trial-to-customer conversion indicates onboarding or product-market fit issues.")
        
        return recommendations
    
    async def predict_churn(self, customer_id: str) -> Dict[str, Any]:
        """Predict customer churn risk"""
        customer = self.customers.get(customer_id)
        if not customer:
            return {"error": "Customer not found"}
        
        # Churn prediction factors
        risk_score = 0.0
        factors = []
        
        # Recency of activity
        days_since_activity = (datetime.now() - customer.last_activity).days
        if days_since_activity > 30:
            risk_score += 0.3
            factors.append(f"No activity for {days_since_activity} days")
        elif days_since_activity > 14:
            risk_score += 0.1
            factors.append(f"Low recent activity ({days_since_activity} days)")
        
        # Engagement decline
        if customer.engagement_score < 5:
            risk_score += 0.2
            factors.append("Low engagement score")
        
        # Stage regression
        if customer.stage_history and len(customer.stage_history) > 1:
            recent_stages = [s["stage"] for s in customer.stage_history[-3:]]
            stage_values = {
                CustomerStage.VISITOR: 1,
                CustomerStage.LEAD: 2,
                CustomerStage.QUALIFIED_LEAD: 3,
                CustomerStage.TRIAL: 4,
                CustomerStage.CUSTOMER: 5,
                CustomerStage.ADVOCATE: 6
            }
            
            if len(recent_stages) >= 2:
                if stage_values[CustomerStage(recent_stages[-1])] < stage_values[CustomerStage(recent_stages[-2])]:
                    risk_score += 0.25
                    factors.append("Recent stage regression detected")
        
        # Low spending (for customers)
        if customer.current_stage == CustomerStage.CUSTOMER and customer.total_spent < 100:
            risk_score += 0.15
            factors.append("Low spending customer")
        
        # Normalize risk score
        risk_score = min(risk_score, 1.0)
        
        # Determine risk level
        if risk_score >= 0.7:
            risk_level = "high"
        elif risk_score >= 0.4:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Generate recommendations
        recommendations = []
        if risk_score >= 0.4:
            recommendations.extend([
                "Reach out with personalized communication",
                "Offer incentives or discounts",
                "Schedule a check-in call or meeting",
                "Provide additional value or resources"
            ])
        
        customer.churn_risk_score = risk_score
        
        return {
            "customer_id": customer_id,
            "churn_risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "risk_factors": factors,
            "recommendations": recommendations,
            "prediction_date": datetime.now().isoformat()
        }
    
    async def get_acquisition_dashboard(self, business_id: str) -> Dict[str, Any]:
        """Get comprehensive customer acquisition dashboard"""
        
        # Get basic metrics
        customers = [c for c in self.customers.values() if c.business_id == business_id]
        campaigns = [c for c in self.campaigns.values() if c.business_id == business_id]
        
        # Current period metrics (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_customers = [c for c in customers if c.acquisition_date >= thirty_days_ago]
        
        # Calculate key metrics
        total_customers = len(customers)
        new_customers_30d = len(recent_customers)
        active_campaigns = len([c for c in campaigns if c.is_active])
        
        # Channel performance
        channel_performance = {}
        for channel in AcquisitionChannel:
            channel_customers = [c for c in customers if c.acquisition_channel == channel]
            channel_performance[channel.value] = {
                "total_customers": len(channel_customers),
                "recent_customers": len([c for c in channel_customers if c.acquisition_date >= thirty_days_ago]),
                "conversion_rate": len([c for c in channel_customers if c.current_stage in [CustomerStage.CUSTOMER, CustomerStage.ADVOCATE]]) / len(channel_customers) if channel_customers else 0
            }
        
        # Calculate CAC and LTV
        cac_data = await self.calculate_customer_acquisition_cost(business_id)
        ltv_data = await self.calculate_lifetime_value(business_id)
        
        # Funnel analysis
        funnel_data = await self.analyze_funnel_performance(business_id)
        
        # Top performing campaigns
        top_campaigns = sorted(campaigns, key=lambda c: c.customers_acquired, reverse=True)[:5]
        
        return {
            "business_id": business_id,
            "summary": {
                "total_customers": total_customers,
                "new_customers_30d": new_customers_30d,
                "active_campaigns": active_campaigns,
                "overall_cac": cac_data.get("overall_cac", 0),
                "overall_ltv": ltv_data.get("overall_ltv", 0),
                "ltv_to_cac_ratio": ltv_data.get("overall_ltv", 0) / cac_data.get("overall_cac", 1) if cac_data.get("overall_cac", 0) > 0 else 0
            },
            "channel_performance": channel_performance,
            "funnel_metrics": {
                "overall_conversion_rate": funnel_data.get("overall_conversion_rate", 0),
                "stage_counts": funnel_data.get("stage_counts", {}),
                "bottlenecks": funnel_data.get("bottlenecks", [])
            },
            "top_campaigns": [
                {
                    "name": c.name,
                    "channel": c.channel,
                    "customers_acquired": c.customers_acquired,
                    "conversion_rate": c.conversion_rate
                } for c in top_campaigns
            ],
            "recent_trends": {
                "daily_acquisitions": self._calculate_daily_trends(recent_customers),
                "channel_trends": self._calculate_channel_trends(customers)
            }
        }
    
    def _calculate_daily_trends(self, customers: List[CustomerRecord]) -> Dict[str, int]:
        """Calculate daily acquisition trends"""
        daily_counts = {}
        for customer in customers:
            date_key = customer.acquisition_date.strftime("%Y-%m-%d")
            daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
        return daily_counts
    
    def _calculate_channel_trends(self, customers: List[CustomerRecord]) -> Dict[str, Dict[str, int]]:
        """Calculate channel performance trends over time"""
        # Simplified version - in production, would analyze historical data
        trends = {}
        for channel in AcquisitionChannel:
            channel_customers = [c for c in customers if c.acquisition_channel == channel]
            trends[channel.value] = {
                "total": len(channel_customers),
                "growth": random.randint(-5, 15)  # Mock growth percentage
            }
        return trends

# Global instance
customer_acquisition_manager = CustomerAcquisitionManager()