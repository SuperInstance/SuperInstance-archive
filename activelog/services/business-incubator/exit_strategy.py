#!/usr/bin/env python3
"""
Exit Strategy Planning System
Comprehensive exit planning and execution platform for businesses

Features:
- Exit strategy assessment and planning
- Acquisition opportunity identification and management
- IPO readiness evaluation and preparation
- Strategic buyer identification and outreach
- Financial buyer (PE/VC) matching
- Valuation optimization for exits
- Due diligence preparation and management
- Transaction process management
- Post-transaction integration planning
- Exit timing optimization
- Tax-efficient structuring strategies
- Management buyout (MBO) facilitation
- Employee stock ownership plan (ESOP) setup
- Succession planning and family transfers
- Exit milestone tracking and reporting
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

class ExitType(str, Enum):
    STRATEGIC_ACQUISITION = "strategic_acquisition"
    FINANCIAL_ACQUISITION = "financial_acquisition"
    IPO = "ipo"
    MANAGEMENT_BUYOUT = "management_buyout"
    EMPLOYEE_BUYOUT = "employee_buyout"
    ESOP = "esop"
    FAMILY_TRANSFER = "family_transfer"
    LIQUIDATION = "liquidation"
    MERGER = "merger"

class ExitStage(str, Enum):
    PLANNING = "planning"
    PREPARATION = "preparation"
    MARKETING = "marketing"
    NEGOTIATION = "negotiation"
    DUE_DILIGENCE = "due_diligence"
    CLOSING = "closing"
    POST_CLOSE = "post_close"
    COMPLETED = "completed"

class BuyerType(str, Enum):
    STRATEGIC = "strategic"  # Industry players
    FINANCIAL = "financial"  # PE/VC funds
    INDIVIDUAL = "individual"  # High-net-worth individuals
    MANAGEMENT = "management"  # Internal team
    EMPLOYEES = "employees"   # Employee group
    FAMILY = "family"        # Family members
    PUBLIC = "public"        # IPO/public markets

class ReadinessLevel(str, Enum):
    NOT_READY = "not_ready"
    EARLY_PREPARATION = "early_preparation" 
    MODERATE_READINESS = "moderate_readiness"
    HIGH_READINESS = "high_readiness"
    EXIT_READY = "exit_ready"

class ExitStrategy(BaseModel):
    id: str
    business_id: str
    strategy_name: str
    
    # Strategy details
    preferred_exit_type: ExitType
    alternative_exit_types: List[ExitType] = []
    target_timeline: int  # months
    minimum_valuation: float
    target_valuation: float
    
    # Objectives
    primary_objectives: List[str] = []  # maximize_value, liquidity, legacy, etc.
    success_criteria: Dict[str, Any] = {}
    
    # Current status
    current_stage: ExitStage = ExitStage.PLANNING
    readiness_level: ReadinessLevel = ReadinessLevel.NOT_READY
    
    # Key stakeholders and their preferences
    stakeholder_preferences: Dict[str, Dict[str, Any]] = {}
    
    # Market conditions and timing
    market_timing_factors: List[str] = []
    optimal_exit_window: Dict[str, datetime] = {}  # start_date, end_date
    
    created_at: datetime
    updated_at: datetime
    created_by: str

class ExitReadinessAssessment(BaseModel):
    id: str
    business_id: str
    assessment_date: datetime
    
    # Financial readiness
    financial_score: float = 0  # 0-100
    financial_factors: Dict[str, Dict[str, Any]] = {}
    
    # Operational readiness  
    operational_score: float = 0  # 0-100
    operational_factors: Dict[str, Dict[str, Any]] = {}
    
    # Legal readiness
    legal_score: float = 0  # 0-100
    legal_factors: Dict[str, Dict[str, Any]] = {}
    
    # Market readiness
    market_score: float = 0  # 0-100
    market_factors: Dict[str, Dict[str, Any]] = {}
    
    # Management readiness
    management_score: float = 0  # 0-100
    management_factors: Dict[str, Dict[str, Any]] = {}
    
    # Overall readiness
    overall_score: float = 0  # 0-100
    readiness_level: ReadinessLevel
    
    # Improvement recommendations
    critical_improvements: List[str] = []
    recommended_improvements: List[str] = []
    timeline_to_ready: int = 0  # months
    
    created_at: datetime
    updated_at: datetime

class PotentialBuyer(BaseModel):
    id: str
    name: str
    buyer_type: BuyerType
    
    # Contact information
    contact_info: Dict[str, str] = {}
    primary_contact: Dict[str, str] = {}
    
    # Buyer profile
    industry_focus: List[str] = []
    geographic_focus: List[str] = []
    size_preferences: Dict[str, float] = {}  # min/max revenue, EBITDA
    
    # Investment criteria
    typical_deal_size: Dict[str, float] = {}  # min, max
    investment_thesis: str = ""
    strategic_rationale: List[str] = []
    
    # Track record
    recent_transactions: List[Dict[str, Any]] = []
    portfolio_companies: List[str] = []
    
    # Matching metrics
    fit_score: float = 0  # 0-100 compatibility with business
    interest_level: str = "unknown"  # unknown, low, medium, high
    
    # Relationship status
    relationship_stage: str = "identified"  # identified, contacted, engaged, negotiating
    last_contact_date: Optional[datetime] = None
    
    created_at: datetime
    updated_at: datetime

class ExitProcess(BaseModel):
    id: str
    business_id: str
    exit_strategy_id: str
    process_name: str
    
    # Process details
    exit_type: ExitType
    current_stage: ExitStage
    target_close_date: Optional[datetime] = None
    
    # Process participants
    advisors: List[Dict[str, str]] = []  # investment_banker, lawyer, accountant, etc.
    potential_buyers: List[str] = []  # buyer IDs
    
    # Process milestones
    milestones: List[Dict[str, Any]] = []
    completed_milestones: List[str] = []
    
    # Documentation
    data_room_url: Optional[str] = None
    marketing_materials: List[str] = []
    legal_documents: List[str] = []
    
    # Financial terms being discussed
    indicative_offers: List[Dict[str, Any]] = []
    letter_of_intent: Optional[Dict[str, Any]] = None
    
    # Due diligence
    dd_requests: List[Dict[str, Any]] = []
    dd_completion_percentage: float = 0
    
    # Status and timeline
    is_active: bool = True
    expected_timeline: int = 0  # months
    
    created_at: datetime
    updated_at: datetime

class PostExitPlan(BaseModel):
    id: str
    business_id: str
    exit_process_id: str
    
    # Post-exit structure
    ownership_retention: float = 0  # Percentage retained post-exit
    management_retention: Dict[str, bool] = {}
    employment_agreements: List[str] = []
    
    # Financial planning
    proceeds_allocation: Dict[str, float] = {}  # taxes, reinvestment, liquidity
    tax_optimization_strategies: List[str] = []
    
    # Transition planning
    integration_timeline: int = 12  # months
    key_transition_milestones: List[str] = []
    cultural_integration_plan: Dict[str, Any] = {}
    
    # Personal objectives
    founder_next_steps: List[str] = []
    employee_retention_plan: Dict[str, Any] = {}
    customer_communication_plan: str = ""
    
    created_at: datetime
    updated_at: datetime

class ExitStrategyManager:
    def __init__(self):
        self.exit_strategies: Dict[str, ExitStrategy] = {}
        self.readiness_assessments: Dict[str, ExitReadinessAssessment] = {}
        self.potential_buyers: Dict[str, PotentialBuyer] = {}
        self.exit_processes: Dict[str, ExitProcess] = {}
        self.post_exit_plans: Dict[str, PostExitPlan] = {}
        
        # Initialize sample buyer database
        self._initialize_sample_buyers()
    
    def _initialize_sample_buyers(self):
        """Initialize sample potential buyers database"""
        sample_buyers = [
            {
                "name": "TechCorp Acquisitions",
                "buyer_type": BuyerType.STRATEGIC,
                "industry_focus": ["SaaS", "Enterprise Software", "AI/ML"],
                "geographic_focus": ["North America", "Europe"],
                "size_preferences": {"min_revenue": 5000000, "max_revenue": 100000000},
                "typical_deal_size": {"min": 10000000, "max": 500000000},
                "strategic_rationale": ["Market expansion", "Technology acquisition", "Talent acquisition"]
            },
            {
                "name": "Growth Equity Partners",
                "buyer_type": BuyerType.FINANCIAL,
                "industry_focus": ["Technology", "Healthcare", "Consumer"],
                "geographic_focus": ["North America"],
                "size_preferences": {"min_ebitda": 2000000, "max_ebitda": 50000000},
                "typical_deal_size": {"min": 25000000, "max": 250000000},
                "strategic_rationale": ["Growth acceleration", "Operational improvement", "Add-on acquisitions"]
            },
            {
                "name": "Vista Equity Partners",
                "buyer_type": BuyerType.FINANCIAL,
                "industry_focus": ["Enterprise Software", "SaaS", "Technology Services"],
                "geographic_focus": ["Global"],
                "size_preferences": {"min_revenue": 20000000, "max_revenue": 2000000000},
                "typical_deal_size": {"min": 100000000, "max": 5000000000},
                "strategic_rationale": ["Technology leadership", "Market consolidation", "Operational excellence"]
            }
        ]
        
        for buyer_data in sample_buyers:
            buyer_id = str(uuid.uuid4())
            buyer = PotentialBuyer(
                id=buyer_id,
                name=buyer_data["name"],
                buyer_type=buyer_data["buyer_type"],
                industry_focus=buyer_data["industry_focus"],
                geographic_focus=buyer_data["geographic_focus"],
                size_preferences=buyer_data["size_preferences"],
                typical_deal_size=buyer_data["typical_deal_size"],
                strategic_rationale=buyer_data["strategic_rationale"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            self.potential_buyers[buyer_id] = buyer
    
    async def create_exit_strategy(
        self, 
        business_id: str, 
        strategy_data: Dict[str, Any]
    ) -> ExitStrategy:
        """Create comprehensive exit strategy for business"""
        
        strategy_id = str(uuid.uuid4())
        
        strategy = ExitStrategy(
            id=strategy_id,
            business_id=business_id,
            strategy_name=strategy_data.get("strategy_name", "Primary Exit Strategy"),
            preferred_exit_type=ExitType(strategy_data.get("preferred_exit_type", "strategic_acquisition")),
            alternative_exit_types=[ExitType(t) for t in strategy_data.get("alternative_exit_types", [])],
            target_timeline=strategy_data.get("target_timeline", 24),  # 24 months default
            minimum_valuation=strategy_data.get("minimum_valuation", 0),
            target_valuation=strategy_data.get("target_valuation", 0),
            primary_objectives=strategy_data.get("primary_objectives", ["maximize_value", "ensure_liquidity"]),
            success_criteria=strategy_data.get("success_criteria", {}),
            stakeholder_preferences=strategy_data.get("stakeholder_preferences", {}),
            market_timing_factors=strategy_data.get("market_timing_factors", []),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            created_by=strategy_data.get("created_by", "user")
        )
        
        self.exit_strategies[strategy_id] = strategy
        return strategy
    
    async def assess_exit_readiness(
        self, 
        business_id: str, 
        assessment_data: Optional[Dict[str, Any]] = None
    ) -> ExitReadinessAssessment:
        """Comprehensive assessment of business exit readiness"""
        
        assessment_id = str(uuid.uuid4())
        
        if not assessment_data:
            assessment_data = {}
        
        # Financial readiness assessment
        financial_assessment = await self._assess_financial_readiness(business_id, assessment_data.get("financial", {}))
        
        # Operational readiness assessment
        operational_assessment = await self._assess_operational_readiness(business_id, assessment_data.get("operational", {}))
        
        # Legal readiness assessment
        legal_assessment = await self._assess_legal_readiness(business_id, assessment_data.get("legal", {}))
        
        # Market readiness assessment
        market_assessment = await self._assess_market_readiness(business_id, assessment_data.get("market", {}))
        
        # Management readiness assessment
        management_assessment = await self._assess_management_readiness(business_id, assessment_data.get("management", {}))
        
        # Calculate overall readiness score
        scores = [
            financial_assessment["score"],
            operational_assessment["score"], 
            legal_assessment["score"],
            market_assessment["score"],
            management_assessment["score"]
        ]
        overall_score = sum(scores) / len(scores)
        
        # Determine readiness level
        if overall_score >= 90:
            readiness_level = ReadinessLevel.EXIT_READY
        elif overall_score >= 75:
            readiness_level = ReadinessLevel.HIGH_READINESS
        elif overall_score >= 60:
            readiness_level = ReadinessLevel.MODERATE_READINESS
        elif overall_score >= 40:
            readiness_level = ReadinessLevel.EARLY_PREPARATION
        else:
            readiness_level = ReadinessLevel.NOT_READY
        
        # Compile recommendations
        all_recommendations = []
        critical_improvements = []
        
        for assessment in [financial_assessment, operational_assessment, legal_assessment, market_assessment, management_assessment]:
            all_recommendations.extend(assessment.get("recommendations", []))
            critical_improvements.extend(assessment.get("critical_issues", []))
        
        # Estimate timeline to readiness
        timeline_to_ready = max(0, int((85 - overall_score) / 5))  # Roughly 5 points improvement per month
        
        assessment = ExitReadinessAssessment(
            id=assessment_id,
            business_id=business_id,
            assessment_date=datetime.now(),
            financial_score=financial_assessment["score"],
            financial_factors=financial_assessment["factors"],
            operational_score=operational_assessment["score"],
            operational_factors=operational_assessment["factors"],
            legal_score=legal_assessment["score"],
            legal_factors=legal_assessment["factors"],
            market_score=market_assessment["score"],
            market_factors=market_assessment["factors"],
            management_score=management_assessment["score"],
            management_factors=management_assessment["factors"],
            overall_score=overall_score,
            readiness_level=readiness_level,
            critical_improvements=critical_improvements,
            recommended_improvements=all_recommendations,
            timeline_to_ready=timeline_to_ready,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.readiness_assessments[assessment_id] = assessment
        return assessment
    
    async def _assess_financial_readiness(self, business_id: str, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess financial readiness for exit"""
        
        score = 0
        factors = {}
        recommendations = []
        critical_issues = []
        
        # Revenue quality and growth (25 points)
        revenue_growth = financial_data.get("revenue_growth", 0)
        revenue_quality = financial_data.get("recurring_revenue_percentage", 0)
        
        if revenue_growth > 0.3:  # 30%+ growth
            score += 25
            factors["revenue_growth"] = {"score": 25, "status": "excellent", "value": revenue_growth}
        elif revenue_growth > 0.15:  # 15%+ growth
            score += 20
            factors["revenue_growth"] = {"score": 20, "status": "good", "value": revenue_growth}
        elif revenue_growth > 0:
            score += 10
            factors["revenue_growth"] = {"score": 10, "status": "moderate", "value": revenue_growth}
            recommendations.append("Accelerate revenue growth to improve exit multiples")
        else:
            factors["revenue_growth"] = {"score": 0, "status": "poor", "value": revenue_growth}
            critical_issues.append("Negative or flat revenue growth")
        
        # Profitability (20 points)
        ebitda_margin = financial_data.get("ebitda_margin", 0)
        if ebitda_margin > 0.2:  # 20%+ EBITDA margin
            score += 20
            factors["profitability"] = {"score": 20, "status": "excellent", "value": ebitda_margin}
        elif ebitda_margin > 0.1:  # 10%+ EBITDA margin
            score += 15
            factors["profitability"] = {"score": 15, "status": "good", "value": ebitda_margin}
        elif ebitda_margin > 0:  # Positive EBITDA
            score += 10
            factors["profitability"] = {"score": 10, "status": "moderate", "value": ebitda_margin}
            recommendations.append("Improve operational efficiency to increase margins")
        else:
            factors["profitability"] = {"score": 0, "status": "poor", "value": ebitda_margin}
            critical_issues.append("Negative EBITDA - path to profitability unclear")
        
        # Financial controls and reporting (15 points)
        has_audited_financials = financial_data.get("has_audited_financials", False)
        financial_controls_score = financial_data.get("financial_controls_score", 0)  # 0-10
        
        controls_score = 0
        if has_audited_financials:
            controls_score += 8
        if financial_controls_score >= 8:
            controls_score += 7
        elif financial_controls_score >= 6:
            controls_score += 4
        
        score += controls_score
        factors["financial_controls"] = {
            "score": controls_score,
            "status": "excellent" if controls_score >= 12 else "good" if controls_score >= 8 else "needs_improvement",
            "has_audited_financials": has_audited_financials,
            "controls_score": financial_controls_score
        }
        
        if not has_audited_financials:
            recommendations.append("Obtain audited financial statements")
        if financial_controls_score < 7:
            recommendations.append("Strengthen financial controls and reporting systems")
        
        # Working capital management (10 points)
        working_capital_days = financial_data.get("working_capital_days", 0)
        if working_capital_days <= 30:
            score += 10
            factors["working_capital"] = {"score": 10, "status": "excellent"}
        elif working_capital_days <= 60:
            score += 7
            factors["working_capital"] = {"score": 7, "status": "good"}
        elif working_capital_days <= 90:
            score += 4
            factors["working_capital"] = {"score": 4, "status": "moderate"}
            recommendations.append("Optimize working capital management")
        else:
            factors["working_capital"] = {"score": 0, "status": "poor"}
            critical_issues.append("Poor working capital management")
        
        # Customer concentration risk (10 points)
        top_customer_percentage = financial_data.get("top_customer_percentage", 0)
        if top_customer_percentage < 0.1:  # <10% concentration
            score += 10
            factors["customer_concentration"] = {"score": 10, "status": "excellent"}
        elif top_customer_percentage < 0.2:  # <20% concentration
            score += 7
            factors["customer_concentration"] = {"score": 7, "status": "good"}
        elif top_customer_percentage < 0.3:  # <30% concentration
            score += 4
            factors["customer_concentration"] = {"score": 4, "status": "moderate"}
            recommendations.append("Diversify customer base to reduce concentration risk")
        else:
            factors["customer_concentration"] = {"score": 0, "status": "high_risk"}
            critical_issues.append("High customer concentration risk")
        
        # Debt and capital structure (10 points)
        debt_to_ebitda = financial_data.get("debt_to_ebitda", 0)
        if debt_to_ebitda < 2:
            score += 10
            factors["capital_structure"] = {"score": 10, "status": "excellent"}
        elif debt_to_ebitda < 3:
            score += 7
            factors["capital_structure"] = {"score": 7, "status": "good"}
        elif debt_to_ebitda < 4:
            score += 4
            factors["capital_structure"] = {"score": 4, "status": "moderate"}
            recommendations.append("Consider debt reduction before exit")
        else:
            factors["capital_structure"] = {"score": 0, "status": "high_leverage"}
            critical_issues.append("High leverage may limit exit options")
        
        # Working capital and cash flow (10 points)
        free_cash_flow_margin = financial_data.get("free_cash_flow_margin", 0)
        if free_cash_flow_margin > 0.15:
            score += 10
            factors["cash_flow"] = {"score": 10, "status": "excellent"}
        elif free_cash_flow_margin > 0.05:
            score += 7
            factors["cash_flow"] = {"score": 7, "status": "good"}
        elif free_cash_flow_margin > 0:
            score += 4
            factors["cash_flow"] = {"score": 4, "status": "moderate"}
        else:
            factors["cash_flow"] = {"score": 0, "status": "negative"}
            critical_issues.append("Negative free cash flow")
        
        return {
            "score": min(score, 100),
            "factors": factors,
            "recommendations": recommendations,
            "critical_issues": critical_issues
        }
    
    async def _assess_operational_readiness(self, business_id: str, operational_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess operational readiness for exit"""
        
        score = 0
        factors = {}
        recommendations = []
        critical_issues = []
        
        # Management team depth (25 points)
        management_depth_score = operational_data.get("management_depth_score", 0)  # 0-10
        key_person_dependency = operational_data.get("key_person_dependency", 10)  # 0-10, lower is better
        
        mgmt_score = 0
        if management_depth_score >= 8:
            mgmt_score += 15
        elif management_depth_score >= 6:
            mgmt_score += 10
        elif management_depth_score >= 4:
            mgmt_score += 5
        
        if key_person_dependency <= 3:
            mgmt_score += 10
        elif key_person_dependency <= 5:
            mgmt_score += 7
        elif key_person_dependency <= 7:
            mgmt_score += 3
        
        score += mgmt_score
        factors["management_team"] = {
            "score": mgmt_score,
            "status": "strong" if mgmt_score >= 20 else "adequate" if mgmt_score >= 10 else "weak",
            "depth_score": management_depth_score,
            "key_person_dependency": key_person_dependency
        }
        
        if management_depth_score < 6:
            recommendations.append("Strengthen management team with key hires")
        if key_person_dependency > 6:
            critical_issues.append("High dependency on key personnel")
        
        # Systems and processes (20 points)
        systems_automation_score = operational_data.get("systems_automation_score", 0)  # 0-10
        process_documentation_score = operational_data.get("process_documentation_score", 0)  # 0-10
        
        systems_score = (systems_automation_score + process_documentation_score) * 1  # Up to 20 points
        score += systems_score
        factors["systems_processes"] = {
            "score": systems_score,
            "status": "advanced" if systems_score >= 16 else "adequate" if systems_score >= 10 else "basic",
            "automation_score": systems_automation_score,
            "documentation_score": process_documentation_score
        }
        
        if systems_automation_score < 6:
            recommendations.append("Invest in systems automation")
        if process_documentation_score < 6:
            recommendations.append("Document key business processes")
        
        # Operational scalability (15 points)
        scalability_score = operational_data.get("scalability_score", 0)  # 0-10
        capacity_utilization = operational_data.get("capacity_utilization", 1.0)  # 0-1
        
        scale_score = scalability_score * 1.5
        if capacity_utilization < 0.8:  # Under 80% utilization = room to grow
            scale_score += 0
        elif capacity_utilization < 0.9:
            scale_score -= 2
        else:
            scale_score -= 5
        
        score += max(0, scale_score)
        factors["scalability"] = {
            "score": scale_score,
            "status": "highly_scalable" if scale_score >= 12 else "scalable" if scale_score >= 8 else "limited",
            "scalability_score": scalability_score,
            "capacity_utilization": capacity_utilization
        }
        
        if scalability_score < 6:
            recommendations.append("Improve operational scalability")
        
        # Quality and compliance (15 points)
        quality_certifications = operational_data.get("quality_certifications", [])
        compliance_score = operational_data.get("compliance_score", 0)  # 0-10
        
        quality_score = len(quality_certifications) * 3 + compliance_score * 1.2
        quality_score = min(quality_score, 15)
        
        score += quality_score
        factors["quality_compliance"] = {
            "score": quality_score,
            "status": "excellent" if quality_score >= 12 else "good" if quality_score >= 8 else "needs_improvement",
            "certifications": quality_certifications,
            "compliance_score": compliance_score
        }
        
        if compliance_score < 7:
            recommendations.append("Strengthen regulatory compliance")
        
        # Customer operations (10 points)
        customer_satisfaction = operational_data.get("customer_satisfaction", 0)  # 0-10
        churn_rate = operational_data.get("annual_churn_rate", 0.5)  # 0-1, lower is better
        
        customer_score = customer_satisfaction
        if churn_rate < 0.05:  # <5% churn
            customer_score += 0
        elif churn_rate < 0.1:  # <10% churn
            customer_score -= 1
        elif churn_rate < 0.2:  # <20% churn
            customer_score -= 3
        else:
            customer_score -= 5
        
        customer_score = max(0, min(customer_score, 10))
        score += customer_score
        factors["customer_operations"] = {
            "score": customer_score,
            "status": "excellent" if customer_score >= 8 else "good" if customer_score >= 6 else "needs_improvement",
            "satisfaction": customer_satisfaction,
            "churn_rate": churn_rate
        }
        
        if customer_satisfaction < 7:
            recommendations.append("Improve customer satisfaction metrics")
        if churn_rate > 0.15:
            critical_issues.append("High customer churn rate")
        
        # Technology infrastructure (15 points)
        technology_score = operational_data.get("technology_score", 0)  # 0-10
        cybersecurity_score = operational_data.get("cybersecurity_score", 0)  # 0-10
        
        tech_score = (technology_score + cybersecurity_score) * 0.75
        score += tech_score
        factors["technology"] = {
            "score": tech_score,
            "status": "advanced" if tech_score >= 12 else "adequate" if tech_score >= 8 else "needs_upgrade",
            "technology_score": technology_score,
            "cybersecurity_score": cybersecurity_score
        }
        
        if technology_score < 6:
            recommendations.append("Modernize technology infrastructure")
        if cybersecurity_score < 7:
            critical_issues.append("Cybersecurity vulnerabilities")
        
        return {
            "score": min(score, 100),
            "factors": factors,
            "recommendations": recommendations,
            "critical_issues": critical_issues
        }
    
    async def _assess_legal_readiness(self, business_id: str, legal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess legal readiness for exit"""
        
        score = 0
        factors = {}
        recommendations = []
        critical_issues = []
        
        # Corporate structure and governance (25 points)
        corporate_structure_score = legal_data.get("corporate_structure_score", 0)  # 0-10
        board_governance_score = legal_data.get("board_governance_score", 0)  # 0-10
        
        governance_score = (corporate_structure_score + board_governance_score) * 1.25
        score += governance_score
        factors["corporate_governance"] = {
            "score": governance_score,
            "status": "excellent" if governance_score >= 20 else "good" if governance_score >= 15 else "needs_improvement",
            "corporate_structure": corporate_structure_score,
            "board_governance": board_governance_score
        }
        
        if corporate_structure_score < 7:
            recommendations.append("Clean up corporate structure and cap table")
        if board_governance_score < 7:
            recommendations.append("Implement proper board governance practices")
        
        # Intellectual property (20 points)
        ip_portfolio_score = legal_data.get("ip_portfolio_score", 0)  # 0-10
        ip_protection_score = legal_data.get("ip_protection_score", 0)  # 0-10
        
        ip_score = (ip_portfolio_score + ip_protection_score)
        score += ip_score
        factors["intellectual_property"] = {
            "score": ip_score,
            "status": "strong" if ip_score >= 16 else "adequate" if ip_score >= 10 else "weak",
            "portfolio_score": ip_portfolio_score,
            "protection_score": ip_protection_score
        }
        
        if ip_portfolio_score < 6:
            recommendations.append("Strengthen IP portfolio and documentation")
        if ip_protection_score < 6:
            critical_issues.append("Inadequate IP protection")
        
        # Contracts and agreements (20 points)
        contract_management_score = legal_data.get("contract_management_score", 0)  # 0-10
        key_agreements_score = legal_data.get("key_agreements_score", 0)  # 0-10
        
        contract_score = (contract_management_score + key_agreements_score)
        score += contract_score
        factors["contracts"] = {
            "score": contract_score,
            "status": "well_managed" if contract_score >= 16 else "adequate" if contract_score >= 10 else "needs_attention",
            "contract_management": contract_management_score,
            "key_agreements": key_agreements_score
        }
        
        if contract_management_score < 6:
            recommendations.append("Improve contract management systems")
        if key_agreements_score < 6:
            critical_issues.append("Key agreements need review and updating")
        
        # Employment and HR legal (15 points)
        employment_compliance_score = legal_data.get("employment_compliance_score", 0)  # 0-10
        has_employment_issues = legal_data.get("has_employment_issues", False)
        
        employment_score = employment_compliance_score * 1.5
        if has_employment_issues:
            employment_score -= 5
        
        employment_score = max(0, employment_score)
        score += employment_score
        factors["employment"] = {
            "score": employment_score,
            "status": "compliant" if employment_score >= 12 else "adequate" if employment_score >= 8 else "issues_exist",
            "compliance_score": employment_compliance_score,
            "has_issues": has_employment_issues
        }
        
        if employment_compliance_score < 7:
            recommendations.append("Address employment law compliance")
        if has_employment_issues:
            critical_issues.append("Outstanding employment-related issues")
        
        # Regulatory and compliance (10 points)
        regulatory_compliance_score = legal_data.get("regulatory_compliance_score", 0)  # 0-10
        
        score += regulatory_compliance_score
        factors["regulatory"] = {
            "score": regulatory_compliance_score,
            "status": "compliant" if regulatory_compliance_score >= 8 else "adequate" if regulatory_compliance_score >= 6 else "non_compliant",
            "compliance_score": regulatory_compliance_score
        }
        
        if regulatory_compliance_score < 6:
            critical_issues.append("Regulatory compliance deficiencies")
        
        # Litigation and disputes (10 points)
        has_material_litigation = legal_data.get("has_material_litigation", False)
        dispute_resolution_score = legal_data.get("dispute_resolution_score", 10)  # 0-10, 10 = no disputes
        
        litigation_score = 10
        if has_material_litigation:
            litigation_score = 0
        else:
            litigation_score = dispute_resolution_score
        
        score += litigation_score
        factors["litigation"] = {
            "score": litigation_score,
            "status": "clean" if litigation_score >= 8 else "manageable" if litigation_score >= 5 else "material_issues",
            "material_litigation": has_material_litigation,
            "dispute_score": dispute_resolution_score
        }
        
        if has_material_litigation:
            critical_issues.append("Material litigation pending")
        
        return {
            "score": min(score, 100),
            "factors": factors,
            "recommendations": recommendations,
            "critical_issues": critical_issues
        }
    
    async def _assess_market_readiness(self, business_id: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess market readiness for exit"""
        
        score = 0
        factors = {}
        recommendations = []
        critical_issues = []
        
        # Market position and competitiveness (30 points)
        market_position_score = market_data.get("market_position_score", 0)  # 0-10
        competitive_advantage_score = market_data.get("competitive_advantage_score", 0)  # 0-10
        brand_strength_score = market_data.get("brand_strength_score", 0)  # 0-10
        
        position_score = (market_position_score + competitive_advantage_score + brand_strength_score)
        score += position_score
        factors["market_position"] = {
            "score": position_score,
            "status": "market_leader" if position_score >= 24 else "strong" if position_score >= 18 else "competitive" if position_score >= 12 else "weak",
            "market_position": market_position_score,
            "competitive_advantage": competitive_advantage_score,
            "brand_strength": brand_strength_score
        }
        
        if market_position_score < 6:
            recommendations.append("Strengthen market position and differentiation")
        if competitive_advantage_score < 6:
            critical_issues.append("Weak competitive advantages")
        
        # Growth potential and market size (25 points)
        market_growth_rate = market_data.get("market_growth_rate", 0)  # Annual growth rate
        addressable_market_size = market_data.get("addressable_market_size", 0)  # $ size
        market_share = market_data.get("market_share", 0)  # 0-1
        
        growth_score = 0
        if market_growth_rate > 0.15:  # 15%+ market growth
            growth_score += 10
        elif market_growth_rate > 0.05:  # 5%+ market growth
            growth_score += 7
        elif market_growth_rate > 0:
            growth_score += 3
        
        if addressable_market_size > 1000000000:  # $1B+ TAM
            growth_score += 8
        elif addressable_market_size > 100000000:  # $100M+ TAM
            growth_score += 5
        elif addressable_market_size > 10000000:  # $10M+ TAM
            growth_score += 2
        
        if market_share > 0.1:  # 10%+ market share
            growth_score += 7
        elif market_share > 0.05:  # 5%+ market share
            growth_score += 4
        elif market_share > 0.01:  # 1%+ market share
            growth_score += 2
        
        score += growth_score
        factors["growth_potential"] = {
            "score": growth_score,
            "status": "high_growth" if growth_score >= 20 else "growth" if growth_score >= 12 else "stable" if growth_score >= 6 else "declining",
            "market_growth": market_growth_rate,
            "market_size": addressable_market_size,
            "market_share": market_share
        }
        
        if market_growth_rate < 0.05:
            recommendations.append("Focus on faster-growing market segments")
        if market_share < 0.01:
            recommendations.append("Build market share and presence")
        
        # Customer base quality (20 points)
        customer_retention_rate = market_data.get("customer_retention_rate", 0)  # 0-1
        customer_satisfaction = market_data.get("customer_satisfaction", 0)  # 0-10
        nps_score = market_data.get("nps_score", 0)  # -100 to +100
        
        customer_score = 0
        if customer_retention_rate > 0.95:  # 95%+ retention
            customer_score += 8
        elif customer_retention_rate > 0.9:  # 90%+ retention
            customer_score += 6
        elif customer_retention_rate > 0.8:  # 80%+ retention
            customer_score += 3
        
        if customer_satisfaction > 8:
            customer_score += 6
        elif customer_satisfaction > 7:
            customer_score += 4
        elif customer_satisfaction > 6:
            customer_score += 2
        
        if nps_score > 50:
            customer_score += 6
        elif nps_score > 30:
            customer_score += 4
        elif nps_score > 0:
            customer_score += 2
        
        score += customer_score
        factors["customer_base"] = {
            "score": customer_score,
            "status": "loyal" if customer_score >= 16 else "satisfied" if customer_score >= 10 else "needs_improvement",
            "retention_rate": customer_retention_rate,
            "satisfaction": customer_satisfaction,
            "nps_score": nps_score
        }
        
        if customer_retention_rate < 0.85:
            recommendations.append("Improve customer retention programs")
        if nps_score < 30:
            recommendations.append("Enhance customer experience and satisfaction")
        
        # Distribution and sales channels (15 points)
        channel_diversification = market_data.get("channel_diversification_score", 0)  # 0-10
        sales_efficiency = market_data.get("sales_efficiency_score", 0)  # 0-10
        
        distribution_score = (channel_diversification + sales_efficiency) * 0.75
        score += distribution_score
        factors["distribution"] = {
            "score": distribution_score,
            "status": "excellent" if distribution_score >= 12 else "good" if distribution_score >= 8 else "needs_improvement",
            "channel_diversification": channel_diversification,
            "sales_efficiency": sales_efficiency
        }
        
        if channel_diversification < 6:
            recommendations.append("Diversify distribution channels")
        if sales_efficiency < 6:
            recommendations.append("Improve sales process efficiency")
        
        # Technology and innovation (10 points)
        innovation_score = market_data.get("innovation_score", 0)  # 0-10
        
        score += innovation_score
        factors["innovation"] = {
            "score": innovation_score,
            "status": "innovative" if innovation_score >= 8 else "adequate" if innovation_score >= 5 else "lagging",
            "innovation_score": innovation_score
        }
        
        if innovation_score < 5:
            recommendations.append("Increase investment in R&D and innovation")
        
        return {
            "score": min(score, 100),
            "factors": factors,
            "recommendations": recommendations,
            "critical_issues": critical_issues
        }
    
    async def _assess_management_readiness(self, business_id: str, management_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess management team readiness for exit"""
        
        score = 0
        factors = {}
        recommendations = []
        critical_issues = []
        
        # Leadership team quality (30 points)
        leadership_experience = management_data.get("leadership_experience_score", 0)  # 0-10
        team_completeness = management_data.get("team_completeness_score", 0)  # 0-10
        succession_planning = management_data.get("succession_planning_score", 0)  # 0-10
        
        leadership_score = (leadership_experience + team_completeness + succession_planning)
        score += leadership_score
        factors["leadership_team"] = {
            "score": leadership_score,
            "status": "strong" if leadership_score >= 24 else "adequate" if leadership_score >= 18 else "needs_strengthening",
            "experience": leadership_experience,
            "completeness": team_completeness,
            "succession_planning": succession_planning
        }
        
        if leadership_experience < 6:
            recommendations.append("Hire experienced executives for key positions")
        if team_completeness < 6:
            critical_issues.append("Key management positions unfilled")
        if succession_planning < 6:
            recommendations.append("Develop succession planning for key roles")
        
        # Organizational structure (20 points)
        org_structure_score = management_data.get("org_structure_score", 0)  # 0-10
        delegation_effectiveness = management_data.get("delegation_effectiveness", 0)  # 0-10
        
        structure_score = (org_structure_score + delegation_effectiveness)
        score += structure_score
        factors["organizational_structure"] = {
            "score": structure_score,
            "status": "well_structured" if structure_score >= 16 else "adequate" if structure_score >= 10 else "needs_improvement",
            "structure_score": org_structure_score,
            "delegation": delegation_effectiveness
        }
        
        if org_structure_score < 6:
            recommendations.append("Improve organizational structure and clarity")
        if delegation_effectiveness < 6:
            critical_issues.append("Over-reliance on founder/CEO")
        
        # Performance management (15 points)
        performance_systems = management_data.get("performance_management_score", 0)  # 0-10
        compensation_structure = management_data.get("compensation_structure_score", 0)  # 0-10
        
        performance_score = (performance_systems + compensation_structure) * 0.75
        score += performance_score
        factors["performance_management"] = {
            "score": performance_score,
            "status": "advanced" if performance_score >= 12 else "adequate" if performance_score >= 8 else "basic",
            "performance_systems": performance_systems,
            "compensation": compensation_structure
        }
        
        if performance_systems < 6:
            recommendations.append("Implement performance management systems")
        if compensation_structure < 6:
            recommendations.append("Align compensation with performance and equity")
        
        # Communication and culture (15 points)
        communication_effectiveness = management_data.get("communication_score", 0)  # 0-10
        culture_strength = management_data.get("culture_strength_score", 0)  # 0-10
        
        culture_score = (communication_effectiveness + culture_strength) * 0.75
        score += culture_score
        factors["culture_communication"] = {
            "score": culture_score,
            "status": "strong" if culture_score >= 12 else "developing" if culture_score >= 8 else "needs_work",
            "communication": communication_effectiveness,
            "culture": culture_strength
        }
        
        if communication_effectiveness < 6:
            recommendations.append("Improve internal communication systems")
        if culture_strength < 6:
            recommendations.append("Strengthen organizational culture")
        
        # Change management capability (10 points)
        change_management_score = management_data.get("change_management_score", 0)  # 0-10
        
        score += change_management_score
        factors["change_management"] = {
            "score": change_management_score,
            "status": "excellent" if change_management_score >= 8 else "adequate" if change_management_score >= 5 else "weak",
            "change_capability": change_management_score
        }
        
        if change_management_score < 5:
            critical_issues.append("Limited change management capability")
        
        # Strategic planning (10 points)
        strategic_planning_score = management_data.get("strategic_planning_score", 0)  # 0-10
        
        score += strategic_planning_score
        factors["strategic_planning"] = {
            "score": strategic_planning_score,
            "status": "advanced" if strategic_planning_score >= 8 else "adequate" if strategic_planning_score >= 5 else "limited",
            "planning_capability": strategic_planning_score
        }
        
        if strategic_planning_score < 5:
            recommendations.append("Strengthen strategic planning capabilities")
        
        return {
            "score": min(score, 100),
            "factors": factors,
            "recommendations": recommendations,
            "critical_issues": critical_issues
        }
    
    async def identify_potential_buyers(
        self, 
        business_id: str, 
        business_profile: Dict[str, Any]
    ) -> List[PotentialBuyer]:
        """Identify and score potential buyers for the business"""
        
        industry = business_profile.get("industry", "")
        revenue = business_profile.get("revenue", 0)
        ebitda = business_profile.get("ebitda", 0)
        geography = business_profile.get("location", "")
        
        matched_buyers = []
        
        for buyer in self.potential_buyers.values():
            # Calculate fit score
            fit_score = await self._calculate_buyer_fit_score(buyer, business_profile)
            
            if fit_score >= 50:  # Minimum fit threshold
                buyer.fit_score = fit_score
                matched_buyers.append(buyer)
        
        # Sort by fit score
        matched_buyers.sort(key=lambda x: x.fit_score, reverse=True)
        
        return matched_buyers
    
    async def _calculate_buyer_fit_score(
        self, 
        buyer: PotentialBuyer, 
        business_profile: Dict[str, Any]
    ) -> float:
        """Calculate how well a buyer fits the business profile"""
        
        score = 0
        
        # Industry fit (30 points)
        business_industry = business_profile.get("industry", "").lower()
        industry_match = False
        
        for buyer_industry in buyer.industry_focus:
            if buyer_industry.lower() in business_industry or business_industry in buyer_industry.lower():
                industry_match = True
                break
        
        if industry_match:
            score += 30
        
        # Size fit (25 points)
        revenue = business_profile.get("revenue", 0)
        ebitda = business_profile.get("ebitda", 0)
        
        size_fit = 0
        
        # Revenue fit
        if "min_revenue" in buyer.size_preferences and "max_revenue" in buyer.size_preferences:
            if buyer.size_preferences["min_revenue"] <= revenue <= buyer.size_preferences["max_revenue"]:
                size_fit += 15
            elif revenue < buyer.size_preferences["min_revenue"]:
                # Penalty for being too small
                ratio = revenue / buyer.size_preferences["min_revenue"]
                size_fit += max(0, 15 * ratio)
            else:
                # Penalty for being too large
                ratio = buyer.size_preferences["max_revenue"] / revenue
                size_fit += max(0, 15 * ratio)
        
        # EBITDA fit
        if "min_ebitda" in buyer.size_preferences and "max_ebitda" in buyer.size_preferences and ebitda > 0:
            if buyer.size_preferences["min_ebitda"] <= ebitda <= buyer.size_preferences["max_ebitda"]:
                size_fit += 10
        
        score += min(size_fit, 25)
        
        # Deal size fit (20 points)
        estimated_value = business_profile.get("estimated_value", revenue * 3)  # Simple 3x revenue multiple
        
        if "min" in buyer.typical_deal_size and "max" in buyer.typical_deal_size:
            if buyer.typical_deal_size["min"] <= estimated_value <= buyer.typical_deal_size["max"]:
                score += 20
            else:
                # Partial score based on proximity
                if estimated_value < buyer.typical_deal_size["min"]:
                    ratio = estimated_value / buyer.typical_deal_size["min"]
                    score += max(0, 20 * ratio)
                else:
                    ratio = buyer.typical_deal_size["max"] / estimated_value
                    score += max(0, 20 * ratio)
        
        # Geographic fit (15 points)
        business_location = business_profile.get("location", "").lower()
        geo_match = False
        
        if not buyer.geographic_focus:  # No geographic restrictions
            geo_match = True
        else:
            for geo in buyer.geographic_focus:
                if geo.lower() in business_location or "global" in geo.lower():
                    geo_match = True
                    break
        
        if geo_match:
            score += 15
        else:
            score += 5  # Partial credit
        
        # Strategic rationale fit (10 points)
        # This would require more sophisticated analysis of strategic fit
        # For now, give partial credit
        score += 7
        
        return min(score, 100)
    
    async def initiate_exit_process(
        self, 
        business_id: str, 
        exit_strategy_id: str, 
        process_config: Dict[str, Any]
    ) -> ExitProcess:
        """Initiate formal exit process"""
        
        process_id = str(uuid.uuid4())
        
        strategy = self.exit_strategies.get(exit_strategy_id)
        if not strategy:
            raise ValueError("Exit strategy not found")
        
        # Create process milestones based on exit type
        milestones = await self._create_exit_milestones(strategy.preferred_exit_type)
        
        process = ExitProcess(
            id=process_id,
            business_id=business_id,
            exit_strategy_id=exit_strategy_id,
            process_name=process_config.get("process_name", f"{strategy.preferred_exit_type.value.title()} Process"),
            exit_type=strategy.preferred_exit_type,
            current_stage=ExitStage.PREPARATION,
            target_close_date=process_config.get("target_close_date"),
            advisors=process_config.get("advisors", []),
            potential_buyers=process_config.get("potential_buyers", []),
            milestones=milestones,
            expected_timeline=process_config.get("expected_timeline", strategy.target_timeline),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.exit_processes[process_id] = process
        return process
    
    async def _create_exit_milestones(self, exit_type: ExitType) -> List[Dict[str, Any]]:
        """Create milestones based on exit type"""
        
        if exit_type == ExitType.STRATEGIC_ACQUISITION:
            return [
                {"name": "Prepare marketing materials", "stage": "preparation", "duration_weeks": 4},
                {"name": "Identify potential buyers", "stage": "preparation", "duration_weeks": 2},
                {"name": "Initial buyer outreach", "stage": "marketing", "duration_weeks": 3},
                {"name": "Management presentations", "stage": "marketing", "duration_weeks": 4},
                {"name": "Receive initial offers", "stage": "negotiation", "duration_weeks": 2},
                {"name": "Letter of Intent", "stage": "negotiation", "duration_weeks": 2},
                {"name": "Due diligence", "stage": "due_diligence", "duration_weeks": 6},
                {"name": "Purchase agreement", "stage": "closing", "duration_weeks": 4},
                {"name": "Regulatory approvals", "stage": "closing", "duration_weeks": 2},
                {"name": "Closing", "stage": "closing", "duration_weeks": 1}
            ]
        elif exit_type == ExitType.IPO:
            return [
                {"name": "Select underwriters", "stage": "preparation", "duration_weeks": 4},
                {"name": "Prepare S-1 registration", "stage": "preparation", "duration_weeks": 12},
                {"name": "SEC review process", "stage": "marketing", "duration_weeks": 8},
                {"name": "Roadshow preparation", "stage": "marketing", "duration_weeks": 2},
                {"name": "Investor roadshow", "stage": "marketing", "duration_weeks": 2},
                {"name": "Price discovery", "stage": "negotiation", "duration_weeks": 1},
                {"name": "Final pricing", "stage": "closing", "duration_weeks": 1},
                {"name": "Trading begins", "stage": "post_close", "duration_weeks": 1}
            ]
        else:
            # Generic milestones
            return [
                {"name": "Prepare for exit", "stage": "preparation", "duration_weeks": 8},
                {"name": "Market to buyers", "stage": "marketing", "duration_weeks": 8},
                {"name": "Negotiate terms", "stage": "negotiation", "duration_weeks": 4},
                {"name": "Due diligence", "stage": "due_diligence", "duration_weeks": 6},
                {"name": "Close transaction", "stage": "closing", "duration_weeks": 4}
            ]
    
    async def get_exit_dashboard(self, business_id: str) -> Dict[str, Any]:
        """Get comprehensive exit planning dashboard"""
        
        # Get exit strategy
        business_strategies = [s for s in self.exit_strategies.values() if s.business_id == business_id]
        business_processes = [p for p in self.exit_processes.values() if p.business_id == business_id]
        business_assessments = [a for a in self.readiness_assessments.values() if a.business_id == business_id]
        
        # Latest readiness assessment
        latest_assessment = None
        if business_assessments:
            latest_assessment = max(business_assessments, key=lambda x: x.assessment_date)
        
        # Active processes
        active_processes = [p for p in business_processes if p.is_active]
        
        # Potential buyers (would normally filter based on business profile)
        top_potential_buyers = list(self.potential_buyers.values())[:10]
        
        return {
            "business_id": business_id,
            "exit_readiness": {
                "overall_score": latest_assessment.overall_score if latest_assessment else 0,
                "readiness_level": latest_assessment.readiness_level.value if latest_assessment else "not_assessed",
                "financial_score": latest_assessment.financial_score if latest_assessment else 0,
                "operational_score": latest_assessment.operational_score if latest_assessment else 0,
                "legal_score": latest_assessment.legal_score if latest_assessment else 0,
                "market_score": latest_assessment.market_score if latest_assessment else 0,
                "management_score": latest_assessment.management_score if latest_assessment else 0,
                "timeline_to_ready": latest_assessment.timeline_to_ready if latest_assessment else None,
                "last_assessed": latest_assessment.assessment_date.isoformat() if latest_assessment else None
            },
            "exit_strategies": [
                {
                    "id": strategy.id,
                    "name": strategy.strategy_name,
                    "preferred_exit_type": strategy.preferred_exit_type.value,
                    "target_valuation": strategy.target_valuation,
                    "target_timeline": strategy.target_timeline,
                    "current_stage": strategy.current_stage.value
                }
                for strategy in business_strategies
            ],
            "active_processes": [
                {
                    "id": process.id,
                    "name": process.process_name,
                    "exit_type": process.exit_type.value,
                    "current_stage": process.current_stage.value,
                    "target_close_date": process.target_close_date.isoformat() if process.target_close_date else None,
                    "milestones_completed": len(process.completed_milestones),
                    "total_milestones": len(process.milestones)
                }
                for process in active_processes
            ],
            "potential_buyers": [
                {
                    "name": buyer.name,
                    "buyer_type": buyer.buyer_type.value,
                    "industry_focus": buyer.industry_focus,
                    "fit_score": buyer.fit_score,
                    "interest_level": buyer.interest_level
                }
                for buyer in top_potential_buyers
            ],
            "key_recommendations": latest_assessment.recommended_improvements[:5] if latest_assessment else [],
            "critical_issues": latest_assessment.critical_improvements[:3] if latest_assessment else [],
            "generated_at": datetime.now().isoformat()
        }

# Global instance
exit_strategy_manager = ExitStrategyManager()