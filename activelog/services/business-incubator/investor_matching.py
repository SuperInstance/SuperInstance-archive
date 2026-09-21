#!/usr/bin/env python3
"""
Investor Matching System
Comprehensive investor-startup matching and relationship management platform

Features:
- Investor profile and preference management
- Startup profile and funding requirements tracking
- AI-powered matching algorithm
- Investment opportunity scoring
- Due diligence document management
- Term sheet generation and negotiation tracking
- Cap table modeling and scenario analysis
- Investment pipeline management
- Investor relations and communication
- Portfolio tracking for investors
- Fundraising milestone tracking
- Market intelligence and trends
- Regulatory compliance monitoring
- Exit planning and investor returns
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

class InvestorType(str, Enum):
    ANGEL = "angel"
    VC = "vc"
    INSTITUTIONAL = "institutional"
    CORPORATE = "corporate"
    GOVERNMENT = "government"
    FAMILY_OFFICE = "family_office"
    ACCELERATOR = "accelerator"
    INCUBATOR = "incubator"

class InvestmentStage(str, Enum):
    PRE_SEED = "pre_seed"
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    SERIES_C = "series_c"
    LATER_STAGE = "later_stage"
    BRIDGE = "bridge"
    CONVERTIBLE = "convertible"

class InvestmentStatus(str, Enum):
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    DUE_DILIGENCE = "due_diligence"
    TERM_SHEET = "term_sheet"
    NEGOTIATING = "negotiating"
    CLOSING = "closing"
    CLOSED = "closed"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

class RiskProfile(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

class InvestorProfile(BaseModel):
    id: str
    name: str
    type: InvestorType
    description: str = ""
    
    # Contact information
    primary_contact: Dict[str, str] = {}  # name, email, phone, title
    location: str = ""
    website: Optional[str] = None
    
    # Investment preferences
    preferred_stages: List[InvestmentStage] = []
    preferred_industries: List[str] = []
    geographic_focus: List[str] = []
    
    # Investment criteria
    ticket_size_min: float = 0
    ticket_size_max: float = 0
    typical_check_size: float = 0
    
    # Portfolio and track record
    portfolio_companies: List[str] = []
    total_investments: int = 0
    successful_exits: int = 0
    
    # Risk and involvement
    risk_tolerance: RiskProfile = RiskProfile.MEDIUM
    involvement_level: str = "hands_off"  # hands_off, advisory, board_member, hands_on
    
    # Investment philosophy
    investment_thesis: str = ""
    value_add: List[str] = []  # mentorship, connections, expertise
    red_flags: List[str] = []
    
    # Operational details
    decision_process: str = ""
    typical_timeline: int = 90  # days
    fund_size: Optional[float] = None
    fund_vintage: Optional[int] = None
    
    # Status
    is_active: bool = True
    is_accepting_deals: bool = True
    last_investment_date: Optional[datetime] = None
    
    created_at: datetime
    updated_at: datetime
    created_by: str

class StartupProfile(BaseModel):
    id: str
    business_id: str
    name: str
    description: str
    
    # Basic information
    industry: str
    sub_industry: Optional[str] = None
    business_model: str
    stage: InvestmentStage = InvestmentStage.SEED
    
    # Team information
    founder_profiles: List[Dict[str, Any]] = []
    team_size: int = 0
    key_hires_needed: List[str] = []
    
    # Market and traction
    target_market: str = ""
    market_size: Dict[str, float] = {}  # TAM, SAM, SOM
    revenue_model: str = ""
    current_revenue: float = 0
    revenue_growth_rate: Optional[float] = None
    customer_count: int = 0
    customer_growth_rate: Optional[float] = None
    
    # Product and technology
    product_status: str = "development"  # concept, development, mvp, launched, scaling
    intellectual_property: List[str] = []
    technology_stack: List[str] = []
    competitive_advantages: List[str] = []
    
    # Financials
    current_valuation: Optional[float] = None
    last_round_valuation: Optional[float] = None
    total_raised: float = 0
    cash_runway: int = 0  # months
    burn_rate: float = 0
    
    # Funding requirements
    seeking_amount: float = 0
    use_of_funds: Dict[str, float] = {}  # category -> amount
    funding_timeline: str = ""
    
    # Due diligence readiness
    financials_ready: bool = False
    legal_ready: bool = False
    ip_ready: bool = False
    team_ready: bool = False
    
    created_at: datetime
    updated_at: datetime

class MatchScore(BaseModel):
    startup_id: str
    investor_id: str
    overall_score: float  # 0-100
    
    # Component scores
    stage_match: float = 0
    industry_match: float = 0
    geography_match: float = 0
    check_size_match: float = 0
    risk_match: float = 0
    
    # Detailed analysis
    matching_criteria: List[str] = []
    concerns: List[str] = []
    recommendations: List[str] = []
    
    # Calculated metrics
    investment_likelihood: float = 0  # 0-1
    strategic_fit: float = 0  # 0-1
    
    calculated_at: datetime

class InvestmentOpportunity(BaseModel):
    id: str
    startup_id: str
    investor_id: str
    
    # Opportunity details
    investment_amount: float
    proposed_valuation: float
    equity_percentage: float
    investment_type: str = "equity"  # equity, convertible, safe
    
    # Status tracking
    status: InvestmentStatus = InvestmentStatus.PROPOSED
    created_date: datetime
    last_updated: datetime
    expected_close_date: Optional[datetime] = None
    
    # Documents and communications
    pitch_deck_url: Optional[str] = None
    data_room_url: Optional[str] = None
    term_sheet_url: Optional[str] = None
    communications: List[Dict[str, Any]] = []
    
    # Due diligence
    due_diligence_items: List[Dict[str, Any]] = []
    due_diligence_completion: float = 0  # percentage
    
    # Terms (if in negotiation)
    proposed_terms: Dict[str, Any] = {}
    negotiation_history: List[Dict[str, Any]] = []
    
    created_at: datetime
    updated_at: datetime

class DueDiligenceItem(BaseModel):
    id: str
    opportunity_id: str
    category: str  # financial, legal, technical, market, team
    item_name: str
    description: str
    
    # Status
    is_completed: bool = False
    completion_date: Optional[datetime] = None
    assigned_to: Optional[str] = None
    
    # Documents
    required_documents: List[str] = []
    provided_documents: List[str] = []
    
    # Assessment
    risk_level: RiskProfile = RiskProfile.MEDIUM
    notes: str = ""
    
    created_at: datetime
    updated_at: datetime

class InvestorMatchingManager:
    def __init__(self):
        self.investors: Dict[str, InvestorProfile] = {}
        self.startups: Dict[str, StartupProfile] = {}
        self.match_scores: Dict[str, MatchScore] = {}  # f"{startup_id}_{investor_id}" -> MatchScore
        self.opportunities: Dict[str, InvestmentOpportunity] = {}
        self.due_diligence_items: Dict[str, DueDiligenceItem] = {}
        
        # Analytics and caching
        self.matching_analytics: Dict[str, Any] = {}
        
        # Initialize sample data
        self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        """Initialize sample investor and startup data"""
        
        # Sample investors
        sample_investors = [
            {
                "name": "TechVentures Capital",
                "type": InvestorType.VC,
                "description": "Early-stage VC focused on B2B SaaS and AI",
                "preferred_stages": [InvestmentStage.SEED, InvestmentStage.SERIES_A],
                "preferred_industries": ["SaaS", "AI/ML", "Enterprise Software"],
                "ticket_size_min": 100000,
                "ticket_size_max": 2000000,
                "typical_check_size": 500000,
                "location": "Silicon Valley",
                "involvement_level": "advisory"
            },
            {
                "name": "Angel Investor Network",
                "type": InvestorType.ANGEL,
                "description": "Network of experienced angel investors",
                "preferred_stages": [InvestmentStage.PRE_SEED, InvestmentStage.SEED],
                "preferred_industries": ["FinTech", "HealthTech", "Consumer"],
                "ticket_size_min": 25000,
                "ticket_size_max": 250000,
                "typical_check_size": 75000,
                "location": "New York",
                "involvement_level": "hands_on"
            },
            {
                "name": "Growth Partners Fund",
                "type": InvestorType.VC,
                "description": "Growth-stage investments in proven businesses",
                "preferred_stages": [InvestmentStage.SERIES_B, InvestmentStage.SERIES_C],
                "preferred_industries": ["E-commerce", "Marketplace", "SaaS"],
                "ticket_size_min": 2000000,
                "ticket_size_max": 20000000,
                "typical_check_size": 5000000,
                "location": "Boston",
                "involvement_level": "board_member"
            }
        ]
        
        for investor_data in sample_investors:
            investor_id = str(uuid.uuid4())
            investor = InvestorProfile(
                id=investor_id,
                name=investor_data["name"],
                type=investor_data["type"],
                description=investor_data["description"],
                preferred_stages=investor_data["preferred_stages"],
                preferred_industries=investor_data["preferred_industries"],
                ticket_size_min=investor_data["ticket_size_min"],
                ticket_size_max=investor_data["ticket_size_max"],
                typical_check_size=investor_data["typical_check_size"],
                location=investor_data["location"],
                involvement_level=investor_data["involvement_level"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                created_by="system"
            )
            self.investors[investor_id] = investor
    
    async def create_investor_profile(self, investor_data: Dict[str, Any]) -> InvestorProfile:
        """Create a new investor profile"""
        investor_id = str(uuid.uuid4())
        
        investor = InvestorProfile(
            id=investor_id,
            name=investor_data["name"],
            type=InvestorType(investor_data.get("type", "vc")),
            description=investor_data.get("description", ""),
            primary_contact=investor_data.get("primary_contact", {}),
            location=investor_data.get("location", ""),
            website=investor_data.get("website"),
            preferred_stages=[InvestmentStage(stage) for stage in investor_data.get("preferred_stages", [])],
            preferred_industries=investor_data.get("preferred_industries", []),
            geographic_focus=investor_data.get("geographic_focus", []),
            ticket_size_min=investor_data.get("ticket_size_min", 0),
            ticket_size_max=investor_data.get("ticket_size_max", 0),
            typical_check_size=investor_data.get("typical_check_size", 0),
            risk_tolerance=RiskProfile(investor_data.get("risk_tolerance", "medium")),
            involvement_level=investor_data.get("involvement_level", "advisory"),
            investment_thesis=investor_data.get("investment_thesis", ""),
            value_add=investor_data.get("value_add", []),
            decision_process=investor_data.get("decision_process", ""),
            typical_timeline=investor_data.get("typical_timeline", 90),
            fund_size=investor_data.get("fund_size"),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            created_by=investor_data.get("created_by", "user")
        )
        
        self.investors[investor_id] = investor
        return investor
    
    async def create_startup_profile(self, startup_data: Dict[str, Any]) -> StartupProfile:
        """Create a new startup profile"""
        startup_id = str(uuid.uuid4())
        
        startup = StartupProfile(
            id=startup_id,
            business_id=startup_data.get("business_id", str(uuid.uuid4())),
            name=startup_data["name"],
            description=startup_data.get("description", ""),
            industry=startup_data.get("industry", ""),
            sub_industry=startup_data.get("sub_industry"),
            business_model=startup_data.get("business_model", ""),
            stage=InvestmentStage(startup_data.get("stage", "seed")),
            founder_profiles=startup_data.get("founder_profiles", []),
            team_size=startup_data.get("team_size", 0),
            target_market=startup_data.get("target_market", ""),
            market_size=startup_data.get("market_size", {}),
            revenue_model=startup_data.get("revenue_model", ""),
            current_revenue=startup_data.get("current_revenue", 0),
            customer_count=startup_data.get("customer_count", 0),
            product_status=startup_data.get("product_status", "development"),
            competitive_advantages=startup_data.get("competitive_advantages", []),
            current_valuation=startup_data.get("current_valuation"),
            total_raised=startup_data.get("total_raised", 0),
            cash_runway=startup_data.get("cash_runway", 0),
            burn_rate=startup_data.get("burn_rate", 0),
            seeking_amount=startup_data.get("seeking_amount", 0),
            use_of_funds=startup_data.get("use_of_funds", {}),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.startups[startup_id] = startup
        return startup
    
    async def calculate_match_scores(self, startup_id: str, investor_ids: Optional[List[str]] = None) -> List[MatchScore]:
        """Calculate match scores between a startup and investors"""
        startup = self.startups.get(startup_id)
        if not startup:
            return []
        
        if investor_ids is None:
            investor_ids = list(self.investors.keys())
        
        match_scores = []
        
        for investor_id in investor_ids:
            investor = self.investors.get(investor_id)
            if not investor or not investor.is_accepting_deals:
                continue
            
            score = await self._calculate_individual_match_score(startup, investor)
            match_scores.append(score)
            
            # Cache the score
            cache_key = f"{startup_id}_{investor_id}"
            self.match_scores[cache_key] = score
        
        # Sort by overall score
        match_scores.sort(key=lambda x: x.overall_score, reverse=True)
        return match_scores
    
    async def _calculate_individual_match_score(self, startup: StartupProfile, investor: InvestorProfile) -> MatchScore:
        """Calculate match score between specific startup and investor"""
        
        # Stage matching (25% weight)
        stage_score = 100 if startup.stage in investor.preferred_stages else 0
        
        # Industry matching (25% weight)
        industry_score = 0
        if investor.preferred_industries:
            for preferred in investor.preferred_industries:
                if preferred.lower() in startup.industry.lower() or (startup.sub_industry and preferred.lower() in startup.sub_industry.lower()):
                    industry_score = 100
                    break
            if industry_score == 0:
                # Partial match for similar industries
                similarity_keywords = {
                    "saas": ["software", "platform", "service"],
                    "fintech": ["financial", "payment", "banking"],
                    "healthtech": ["health", "medical", "wellness"],
                    "ecommerce": ["retail", "marketplace", "commerce"]
                }
                for pref in investor.preferred_industries:
                    if pref.lower() in similarity_keywords:
                        for keyword in similarity_keywords[pref.lower()]:
                            if keyword in startup.industry.lower():
                                industry_score = 60
                                break
        else:
            industry_score = 50  # Neutral if no industry preference
        
        # Check size matching (20% weight)
        check_size_score = 0
        if investor.ticket_size_min <= startup.seeking_amount <= investor.ticket_size_max:
            check_size_score = 100
        elif startup.seeking_amount < investor.ticket_size_min:
            # Calculate penalty based on gap
            gap_ratio = investor.ticket_size_min / startup.seeking_amount if startup.seeking_amount > 0 else 10
            check_size_score = max(0, 100 - (gap_ratio - 1) * 50)
        else:  # startup.seeking_amount > investor.ticket_size_max
            gap_ratio = startup.seeking_amount / investor.ticket_size_max
            check_size_score = max(0, 100 - (gap_ratio - 1) * 30)
        
        # Geographic matching (10% weight)
        geography_score = 50  # Default neutral score
        if investor.geographic_focus:
            for geo in investor.geographic_focus:
                # Simple location matching - in production would use more sophisticated geo-matching
                if geo.lower() in startup.business_id.lower():  # Simplified - would use actual location data
                    geography_score = 100
                    break
        
        # Risk matching (20% weight)
        risk_score = 50  # Default neutral
        startup_risk_indicators = {
            "pre_seed": RiskProfile.VERY_HIGH,
            "seed": RiskProfile.HIGH,
            "series_a": RiskProfile.MEDIUM,
            "series_b": RiskProfile.MEDIUM,
            "series_c": RiskProfile.LOW
        }
        
        startup_risk = startup_risk_indicators.get(startup.stage.value, RiskProfile.MEDIUM)
        
        risk_compatibility = {
            (RiskProfile.VERY_HIGH, RiskProfile.VERY_HIGH): 100,
            (RiskProfile.VERY_HIGH, RiskProfile.HIGH): 80,
            (RiskProfile.HIGH, RiskProfile.HIGH): 100,
            (RiskProfile.HIGH, RiskProfile.MEDIUM): 90,
            (RiskProfile.MEDIUM, RiskProfile.MEDIUM): 100,
            (RiskProfile.MEDIUM, RiskProfile.LOW): 70,
            (RiskProfile.LOW, RiskProfile.LOW): 100
        }
        
        risk_score = risk_compatibility.get((startup_risk, investor.risk_tolerance), 50)
        
        # Calculate weighted overall score
        overall_score = (
            stage_score * 0.25 +
            industry_score * 0.25 +
            check_size_score * 0.20 +
            geography_score * 0.10 +
            risk_score * 0.20
        )
        
        # Generate matching criteria and concerns
        matching_criteria = []
        concerns = []
        recommendations = []
        
        if stage_score == 100:
            matching_criteria.append(f"Perfect stage match: {startup.stage.value}")
        elif stage_score == 0:
            concerns.append(f"Stage mismatch: Startup is {startup.stage.value}, investor prefers {', '.join([s.value for s in investor.preferred_stages])}")
        
        if industry_score == 100:
            matching_criteria.append("Strong industry alignment")
        elif industry_score == 0:
            concerns.append("No industry overlap")
            
        if check_size_score >= 80:
            matching_criteria.append("Good check size fit")
        elif check_size_score < 50:
            if startup.seeking_amount < investor.ticket_size_min:
                concerns.append(f"Funding ask too small (${startup.seeking_amount:,.0f} vs min ${investor.ticket_size_min:,.0f})")
                recommendations.append("Consider raising a larger round or finding smaller check investors")
            else:
                concerns.append(f"Funding ask too large (${startup.seeking_amount:,.0f} vs max ${investor.ticket_size_max:,.0f})")
                recommendations.append("Consider breaking round into tranches or finding larger investors")
        
        # Calculate derived metrics
        investment_likelihood = min(overall_score / 100, 1.0)
        strategic_fit = (stage_score + industry_score) / 200  # Based on most important criteria
        
        return MatchScore(
            startup_id=startup.id,
            investor_id=investor.id,
            overall_score=round(overall_score, 1),
            stage_match=stage_score,
            industry_match=industry_score,
            geography_match=geography_score,
            check_size_match=check_size_score,
            risk_match=risk_score,
            matching_criteria=matching_criteria,
            concerns=concerns,
            recommendations=recommendations,
            investment_likelihood=round(investment_likelihood, 2),
            strategic_fit=round(strategic_fit, 2),
            calculated_at=datetime.now()
        )
    
    async def create_investment_opportunity(
        self, 
        startup_id: str, 
        investor_id: str, 
        opportunity_data: Dict[str, Any]
    ) -> InvestmentOpportunity:
        """Create a new investment opportunity"""
        
        startup = self.startups.get(startup_id)
        investor = self.investors.get(investor_id)
        
        if not startup or not investor:
            raise ValueError("Invalid startup or investor ID")
        
        opportunity_id = str(uuid.uuid4())
        
        opportunity = InvestmentOpportunity(
            id=opportunity_id,
            startup_id=startup_id,
            investor_id=investor_id,
            investment_amount=opportunity_data.get("investment_amount", startup.seeking_amount),
            proposed_valuation=opportunity_data.get("proposed_valuation", startup.current_valuation or 0),
            equity_percentage=opportunity_data.get("equity_percentage", 0),
            investment_type=opportunity_data.get("investment_type", "equity"),
            status=InvestmentStatus(opportunity_data.get("status", "proposed")),
            created_date=datetime.now(),
            last_updated=datetime.now(),
            expected_close_date=opportunity_data.get("expected_close_date"),
            pitch_deck_url=opportunity_data.get("pitch_deck_url"),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Calculate equity percentage if not provided
        if opportunity.equity_percentage == 0 and opportunity.proposed_valuation > 0:
            opportunity.equity_percentage = (opportunity.investment_amount / opportunity.proposed_valuation) * 100
        
        self.opportunities[opportunity_id] = opportunity
        
        # Create default due diligence items
        await self._create_default_due_diligence(opportunity_id)
        
        return opportunity
    
    async def _create_default_due_diligence(self, opportunity_id: str):
        """Create default due diligence items for an opportunity"""
        default_items = [
            {"category": "financial", "item_name": "Financial Statements", "description": "Last 3 years of financial statements"},
            {"category": "financial", "item_name": "Management Accounts", "description": "Current year management accounts"},
            {"category": "legal", "item_name": "Corporate Structure", "description": "Articles of incorporation, bylaws, cap table"},
            {"category": "legal", "item_name": "Contracts", "description": "Major customer and supplier contracts"},
            {"category": "legal", "item_name": "Employment Agreements", "description": "Key employee agreements and equity grants"},
            {"category": "technical", "item_name": "IP Portfolio", "description": "Patents, trademarks, copyrights"},
            {"category": "technical", "item_name": "Code Review", "description": "Technical architecture and code quality assessment"},
            {"category": "market", "item_name": "Market Analysis", "description": "Customer research and competitive analysis"},
            {"category": "team", "item_name": "Reference Checks", "description": "Background checks on key team members"}
        ]
        
        for item_data in default_items:
            item_id = str(uuid.uuid4())
            
            item = DueDiligenceItem(
                id=item_id,
                opportunity_id=opportunity_id,
                category=item_data["category"],
                item_name=item_data["item_name"],
                description=item_data["description"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.due_diligence_items[item_id] = item
    
    async def update_opportunity_status(
        self, 
        opportunity_id: str, 
        new_status: InvestmentStatus, 
        notes: str = ""
    ) -> bool:
        """Update investment opportunity status"""
        opportunity = self.opportunities.get(opportunity_id)
        if not opportunity:
            return False
        
        old_status = opportunity.status
        opportunity.status = new_status
        opportunity.last_updated = datetime.now()
        
        # Add communication record
        opportunity.communications.append({
            "timestamp": datetime.now().isoformat(),
            "type": "status_change",
            "content": f"Status changed from {old_status} to {new_status}",
            "notes": notes
        })
        
        # Update due diligence completion if moving to due diligence stage
        if new_status == InvestmentStatus.DUE_DILIGENCE:
            opportunity.due_diligence_completion = await self._calculate_due_diligence_completion(opportunity_id)
        
        return True
    
    async def _calculate_due_diligence_completion(self, opportunity_id: str) -> float:
        """Calculate due diligence completion percentage"""
        dd_items = [item for item in self.due_diligence_items.values() if item.opportunity_id == opportunity_id]
        
        if not dd_items:
            return 0.0
        
        completed_items = len([item for item in dd_items if item.is_completed])
        return (completed_items / len(dd_items)) * 100
    
    async def complete_due_diligence_item(self, item_id: str, completion_data: Dict[str, Any]) -> bool:
        """Mark a due diligence item as completed"""
        item = self.due_diligence_items.get(item_id)
        if not item:
            return False
        
        item.is_completed = True
        item.completion_date = datetime.now()
        item.notes = completion_data.get("notes", "")
        item.risk_level = RiskProfile(completion_data.get("risk_level", "medium"))
        item.provided_documents = completion_data.get("provided_documents", [])
        item.updated_at = datetime.now()
        
        # Update overall due diligence completion for the opportunity
        opportunity = self.opportunities.get(item.opportunity_id)
        if opportunity:
            opportunity.due_diligence_completion = await self._calculate_due_diligence_completion(item.opportunity_id)
        
        return True
    
    async def generate_term_sheet(self, opportunity_id: str, terms: Dict[str, Any]) -> Dict[str, Any]:
        """Generate term sheet for investment opportunity"""
        opportunity = self.opportunities.get(opportunity_id)
        if not opportunity:
            return {}
        
        startup = self.startups.get(opportunity.startup_id)
        investor = self.investors.get(opportunity.investor_id)
        
        if not startup or not investor:
            return {}
        
        # Standard term sheet structure
        term_sheet = {
            "term_sheet_id": str(uuid.uuid4()),
            "opportunity_id": opportunity_id,
            "generated_date": datetime.now().isoformat(),
            
            # Basic terms
            "company_name": startup.name,
            "investor_name": investor.name,
            "investment_amount": terms.get("investment_amount", opportunity.investment_amount),
            "valuation": {
                "pre_money": terms.get("pre_money_valuation", opportunity.proposed_valuation),
                "post_money": 0  # Will be calculated
            },
            "equity_percentage": 0,  # Will be calculated
            "security_type": terms.get("security_type", "Preferred Stock"),
            
            # Preferences
            "liquidation_preference": terms.get("liquidation_preference", "1x Non-Participating"),
            "dividend_rate": terms.get("dividend_rate", "8% cumulative"),
            "anti_dilution": terms.get("anti_dilution", "Weighted Average Broad Based"),
            
            # Control provisions
            "board_composition": terms.get("board_composition", "Founder majority"),
            "voting_rights": terms.get("voting_rights", "Standard protective provisions"),
            "information_rights": terms.get("information_rights", "Standard monthly/quarterly reporting"),
            
            # Other terms
            "drag_along": terms.get("drag_along", True),
            "tag_along": terms.get("tag_along", True),
            "right_of_first_refusal": terms.get("right_of_first_refusal", True),
            "option_pool": terms.get("option_pool", "15% allocated to employee pool"),
            
            # Timeline
            "expiration_date": (datetime.now() + timedelta(days=30)).isoformat(),
            "closing_conditions": terms.get("closing_conditions", [
                "Completion of due diligence",
                "Execution of definitive agreements",
                "No material adverse changes"
            ])
        }
        
        # Calculate derived values
        investment_amount = term_sheet["investment_amount"]
        pre_money = term_sheet["valuation"]["pre_money"]
        post_money = pre_money + investment_amount
        
        term_sheet["valuation"]["post_money"] = post_money
        term_sheet["equity_percentage"] = (investment_amount / post_money) * 100
        
        # Store proposed terms in opportunity
        opportunity.proposed_terms = term_sheet
        opportunity.updated_at = datetime.now()
        
        return term_sheet
    
    async def get_investor_pipeline(self, investor_id: str) -> Dict[str, Any]:
        """Get investment pipeline for an investor"""
        investor = self.investors.get(investor_id)
        if not investor:
            return {}
        
        # Get all opportunities for this investor
        investor_opportunities = [opp for opp in self.opportunities.values() if opp.investor_id == investor_id]
        
        # Group by status
        pipeline = {}
        for status in InvestmentStatus:
            status_opportunities = [opp for opp in investor_opportunities if opp.status == status]
            
            pipeline[status.value] = {
                "count": len(status_opportunities),
                "total_amount": sum(opp.investment_amount for opp in status_opportunities),
                "opportunities": [
                    {
                        "id": opp.id,
                        "startup_name": self.startups.get(opp.startup_id, {}).name if self.startups.get(opp.startup_id) else "Unknown",
                        "amount": opp.investment_amount,
                        "valuation": opp.proposed_valuation,
                        "equity": opp.equity_percentage,
                        "created_date": opp.created_date.isoformat(),
                        "expected_close": opp.expected_close_date.isoformat() if opp.expected_close_date else None
                    }
                    for opp in status_opportunities
                ]
            }
        
        # Calculate summary metrics
        total_pipeline_value = sum(opp.investment_amount for opp in investor_opportunities if opp.status not in [InvestmentStatus.REJECTED, InvestmentStatus.WITHDRAWN])
        active_deals = len([opp for opp in investor_opportunities if opp.status in [InvestmentStatus.UNDER_REVIEW, InvestmentStatus.DUE_DILIGENCE, InvestmentStatus.NEGOTIATING]])
        
        return {
            "investor_id": investor_id,
            "investor_name": investor.name,
            "summary": {
                "total_opportunities": len(investor_opportunities),
                "active_deals": active_deals,
                "total_pipeline_value": total_pipeline_value,
                "avg_deal_size": total_pipeline_value / len(investor_opportunities) if investor_opportunities else 0
            },
            "pipeline": pipeline,
            "generated_at": datetime.now().isoformat()
        }
    
    async def get_startup_fundraising_status(self, startup_id: str) -> Dict[str, Any]:
        """Get fundraising status for a startup"""
        startup = self.startups.get(startup_id)
        if not startup:
            return {}
        
        # Get all opportunities for this startup
        startup_opportunities = [opp for opp in self.opportunities.values() if opp.startup_id == startup_id]
        
        # Calculate fundraising metrics
        total_committed = sum(opp.investment_amount for opp in startup_opportunities if opp.status == InvestmentStatus.CLOSED)
        total_pipeline = sum(opp.investment_amount for opp in startup_opportunities if opp.status not in [InvestmentStatus.REJECTED, InvestmentStatus.WITHDRAWN, InvestmentStatus.CLOSED])
        
        # Progress towards funding goal
        funding_progress = (total_committed / startup.seeking_amount) * 100 if startup.seeking_amount > 0 else 0
        pipeline_coverage = ((total_committed + total_pipeline) / startup.seeking_amount) * 100 if startup.seeking_amount > 0 else 0
        
        # Investor status breakdown
        investor_status = {}
        for opp in startup_opportunities:
            investor = self.investors.get(opp.investor_id)
            investor_name = investor.name if investor else "Unknown"
            
            investor_status[investor_name] = {
                "status": opp.status.value,
                "amount": opp.investment_amount,
                "equity": opp.equity_percentage,
                "last_updated": opp.last_updated.isoformat()
            }
        
        # Recent activity
        recent_activities = []
        for opp in sorted(startup_opportunities, key=lambda x: x.last_updated, reverse=True)[:5]:
            investor = self.investors.get(opp.investor_id)
            recent_activities.append({
                "investor": investor.name if investor else "Unknown",
                "activity": f"Status: {opp.status.value}",
                "date": opp.last_updated.isoformat()
            })
        
        return {
            "startup_id": startup_id,
            "startup_name": startup.name,
            "fundraising_goal": startup.seeking_amount,
            "progress": {
                "committed": total_committed,
                "pipeline": total_pipeline,
                "funding_progress_percentage": round(funding_progress, 1),
                "pipeline_coverage_percentage": round(pipeline_coverage, 1)
            },
            "investor_count": {
                "total_approached": len(startup_opportunities),
                "active_discussions": len([opp for opp in startup_opportunities if opp.status in [InvestmentStatus.UNDER_REVIEW, InvestmentStatus.DUE_DILIGENCE, InvestmentStatus.NEGOTIATING]]),
                "committed": len([opp for opp in startup_opportunities if opp.status == InvestmentStatus.CLOSED])
            },
            "investor_status": investor_status,
            "recent_activities": recent_activities,
            "generated_at": datetime.now().isoformat()
        }
    
    async def get_market_intelligence(self, industry: Optional[str] = None, stage: Optional[InvestmentStage] = None) -> Dict[str, Any]:
        """Get market intelligence and funding trends"""
        
        # Filter opportunities based on criteria
        relevant_opportunities = list(self.opportunities.values())
        
        if industry:
            startup_ids = [s.id for s in self.startups.values() if industry.lower() in s.industry.lower()]
            relevant_opportunities = [opp for opp in relevant_opportunities if opp.startup_id in startup_ids]
        
        if stage:
            startup_ids = [s.id for s in self.startups.values() if s.stage == stage]
            relevant_opportunities = [opp for opp in relevant_opportunities if opp.startup_id in startup_ids]
        
        # Calculate market metrics
        total_deals = len(relevant_opportunities)
        closed_deals = [opp for opp in relevant_opportunities if opp.status == InvestmentStatus.CLOSED]
        
        if not closed_deals:
            return {"error": "Insufficient data for market analysis"}
        
        # Valuation metrics
        valuations = [opp.proposed_valuation for opp in closed_deals if opp.proposed_valuation > 0]
        check_sizes = [opp.investment_amount for opp in closed_deals]
        
        market_data = {
            "market_overview": {
                "total_deals_tracked": total_deals,
                "closed_deals": len(closed_deals),
                "success_rate": (len(closed_deals) / total_deals * 100) if total_deals > 0 else 0,
                "total_funding": sum(check_sizes),
                "average_deal_size": statistics.mean(check_sizes) if check_sizes else 0
            },
            "valuation_metrics": {
                "median_valuation": statistics.median(valuations) if valuations else 0,
                "average_valuation": statistics.mean(valuations) if valuations else 0,
                "valuation_range": {
                    "min": min(valuations) if valuations else 0,
                    "max": max(valuations) if valuations else 0
                }
            },
            "timing_metrics": {
                "average_fundraising_duration": "90 days",  # Simplified
                "due_diligence_duration": "30 days"  # Simplified
            },
            "trends": {
                "hot_sectors": ["AI/ML", "FinTech", "HealthTech"],  # Mock data
                "emerging_themes": ["Sustainability", "Remote Work", "Digital Health"],
                "funding_velocity": "Increasing",  # Simplified trend analysis
                "investor_appetite": "Strong"
            },
            "analysis_date": datetime.now().isoformat(),
            "data_points": len(closed_deals)
        }
        
        return market_data
    
    async def get_matching_dashboard(self, user_type: str, user_id: str) -> Dict[str, Any]:
        """Get comprehensive matching dashboard for investors or startups"""
        
        if user_type == "investor":
            return await self._get_investor_dashboard(user_id)
        elif user_type == "startup":
            return await self._get_startup_dashboard(user_id)
        else:
            return {"error": "Invalid user type"}
    
    async def _get_investor_dashboard(self, investor_id: str) -> Dict[str, Any]:
        """Get investor-specific dashboard"""
        investor = self.investors.get(investor_id)
        if not investor:
            return {"error": "Investor not found"}
        
        # Get pipeline data
        pipeline = await self.get_investor_pipeline(investor_id)
        
        # Get top matching startups
        all_startups = list(self.startups.keys())
        top_matches = []
        if all_startups:
            # Calculate matches for a few startups (in production, would be more sophisticated)
            for startup_id in all_startups[:10]:  # Limit for demo
                matches = await self.calculate_match_scores(startup_id, [investor_id])
                if matches:
                    match = matches[0]
                    startup = self.startups[startup_id]
                    top_matches.append({
                        "startup_name": startup.name,
                        "startup_id": startup_id,
                        "match_score": match.overall_score,
                        "industry": startup.industry,
                        "stage": startup.stage.value,
                        "seeking_amount": startup.seeking_amount
                    })
        
        top_matches.sort(key=lambda x: x["match_score"], reverse=True)
        
        return {
            "investor_id": investor_id,
            "investor_name": investor.name,
            "dashboard_type": "investor",
            "summary": pipeline["summary"],
            "active_pipeline": pipeline["pipeline"],
            "top_matching_startups": top_matches[:5],
            "investment_preferences": {
                "preferred_stages": [stage.value for stage in investor.preferred_stages],
                "preferred_industries": investor.preferred_industries,
                "check_size_range": f"${investor.ticket_size_min:,.0f} - ${investor.ticket_size_max:,.0f}"
            },
            "recent_activity": [
                {"activity": "Reviewed new deal", "date": datetime.now().isoformat()},
                {"activity": "Completed due diligence", "date": (datetime.now() - timedelta(days=2)).isoformat()}
            ],
            "generated_at": datetime.now().isoformat()
        }
    
    async def _get_startup_dashboard(self, startup_id: str) -> Dict[str, Any]:
        """Get startup-specific dashboard"""
        startup = self.startups.get(startup_id)
        if not startup:
            return {"error": "Startup not found"}
        
        # Get fundraising status
        fundraising_status = await self.get_startup_fundraising_status(startup_id)
        
        # Get top matching investors
        top_matches = await self.calculate_match_scores(startup_id)
        
        matching_investors = []
        for match in top_matches[:5]:
            investor = self.investors[match.investor_id]
            matching_investors.append({
                "investor_name": investor.name,
                "investor_id": investor.id,
                "match_score": match.overall_score,
                "investor_type": investor.type.value,
                "typical_check_size": investor.typical_check_size,
                "matching_criteria": match.matching_criteria
            })
        
        return {
            "startup_id": startup_id,
            "startup_name": startup.name,
            "dashboard_type": "startup",
            "fundraising_status": fundraising_status,
            "top_matching_investors": matching_investors,
            "company_profile": {
                "industry": startup.industry,
                "stage": startup.stage.value,
                "seeking_amount": startup.seeking_amount,
                "current_valuation": startup.current_valuation,
                "revenue": startup.current_revenue
            },
            "readiness_checklist": {
                "financials_ready": startup.financials_ready,
                "legal_ready": startup.legal_ready,
                "ip_ready": startup.ip_ready,
                "team_ready": startup.team_ready,
                "overall_readiness": sum([startup.financials_ready, startup.legal_ready, startup.ip_ready, startup.team_ready]) / 4 * 100
            },
            "generated_at": datetime.now().isoformat()
        }

# Global instance
investor_matching_manager = InvestorMatchingManager()