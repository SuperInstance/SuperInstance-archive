"""
Frontend Valuation System
Comprehensive valuation engine for frontend assets using multiple methodologies
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import asyncio
import logging
import json
import sqlite3
import numpy as np
from decimal import Decimal, ROUND_HALF_UP
import math

logger = logging.getLogger(__name__)

class ValuationMethod(str, Enum):
    DCF = "dcf"                    # Discounted Cash Flow
    COMPARABLE = "comparable"       # Market Comparables
    COST = "cost"                  # Cost-based approach
    REVENUE_MULTIPLE = "revenue_multiple"  # Revenue multiple
    USER_MULTIPLE = "user_multiple"        # User-based valuation
    TECH_STACK = "tech_stack"             # Technology stack value
    DOMAIN_AUTHORITY = "domain_authority"  # SEO/domain value
    HYBRID = "hybrid"                     # Combined approach

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

class ValuationComponent(BaseModel):
    component_name: str
    method: ValuationMethod
    value: Decimal
    weight: float = 1.0
    confidence: float = 1.0
    
    # Supporting data
    assumptions: Dict[str, Any] = {}
    calculations: Dict[str, float] = {}
    risk_factors: List[str] = []
    
    notes: str = ""

class MarketComparable(BaseModel):
    id: str
    name: str
    url: Optional[str] = None
    
    # Financial metrics
    revenue: Decimal
    user_count: int
    valuation: Decimal
    
    # Technical similarities
    framework: str
    category: str
    complexity_score: float
    
    # Market data
    funding_stage: str = "unknown"
    last_transaction_date: Optional[datetime] = None
    
    similarity_score: float = 0.0  # 0-1 similarity to target

class ValuationReport(BaseModel):
    id: str
    frontend_id: str
    valuator_id: str
    
    # Final valuation
    base_valuation: Decimal
    risk_adjusted_valuation: Decimal
    valuation_range_low: Decimal
    valuation_range_high: Decimal
    
    # Method breakdown
    valuation_components: List[ValuationComponent]
    primary_method: ValuationMethod
    
    # Risk assessment
    overall_risk_level: RiskLevel
    risk_factors: List[Dict[str, Any]] = []
    risk_discount: float = 0.0  # Percentage discount for risk
    
    # Market context
    market_conditions: Dict[str, Any] = {}
    comparable_transactions: List[MarketComparable] = []
    
    # Metadata
    valuation_date: datetime
    validity_period_days: int = 90
    methodology_notes: str = ""
    
    # Growth projections
    projected_growth_rate: float = 0.0
    growth_assumptions: Dict[str, Any] = {}

class FrontendAsset(BaseModel):
    id: str
    name: str
    
    # Financial metrics
    monthly_revenue: Decimal = Decimal('0')
    annual_revenue: Decimal = Decimal('0')
    revenue_growth_rate: float = 0.0
    
    # User metrics
    monthly_active_users: int = 0
    user_growth_rate: float = 0.0
    user_lifetime_value: Decimal = Decimal('0')
    
    # Technical metrics
    framework: str
    lines_of_code: int = 0
    technical_debt_score: float = 0.0
    performance_score: float = 0.0
    
    # Development costs
    development_time_hours: int = 0
    hourly_rate: Decimal = Decimal('50')
    maintenance_cost_monthly: Decimal = Decimal('0')
    
    # Market position
    category: str = ""
    competitive_advantage: str = ""
    domain_authority: float = 0.0
    seo_score: float = 0.0
    
    # Asset quality
    code_quality_score: float = 0.0
    documentation_completeness: float = 0.0
    test_coverage: float = 0.0
    
    # Legal/IP
    has_trademark: bool = False
    has_patents: bool = False
    license_type: str = "open_source"

class FrontendValuationManager:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/frontend-market/data/frontend_valuation.db"
        self.init_database()
        
        # Market multipliers by category
        self.category_multipliers = {
            "ecommerce": {"revenue": 3.5, "user": 120},
            "saas": {"revenue": 8.2, "user": 200},
            "media": {"revenue": 2.1, "user": 85},
            "social": {"revenue": 12.5, "user": 180},
            "gaming": {"revenue": 4.8, "user": 95},
            "education": {"revenue": 6.2, "user": 150},
            "healthcare": {"revenue": 7.8, "user": 250},
            "fintech": {"revenue": 15.2, "user": 400},
            "default": {"revenue": 4.0, "user": 100}
        }
        
        # Risk factors and their impact
        self.risk_factors = {
            "high_technical_debt": 0.15,
            "single_developer": 0.12,
            "no_documentation": 0.10,
            "deprecated_framework": 0.25,
            "security_vulnerabilities": 0.20,
            "no_tests": 0.08,
            "performance_issues": 0.12,
            "legal_issues": 0.30,
            "market_decline": 0.18,
            "high_competition": 0.10
        }
    
    def init_database(self):
        """Initialize valuation database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Valuation reports table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS valuation_reports (
                id TEXT PRIMARY KEY,
                frontend_id TEXT NOT NULL,
                valuator_id TEXT NOT NULL,
                base_valuation DECIMAL NOT NULL,
                risk_adjusted_valuation DECIMAL NOT NULL,
                primary_method TEXT NOT NULL,
                overall_risk_level TEXT NOT NULL,
                data TEXT NOT NULL,
                valuation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Market comparables table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_comparables (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                framework TEXT NOT NULL,
                category TEXT NOT NULL,
                revenue DECIMAL NOT NULL,
                user_count INTEGER NOT NULL,
                valuation DECIMAL NOT NULL,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Valuation components table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS valuation_components (
                id TEXT PRIMARY KEY,
                valuation_report_id TEXT NOT NULL,
                component_name TEXT NOT NULL,
                method TEXT NOT NULL,
                value DECIMAL NOT NULL,
                weight REAL NOT NULL,
                confidence REAL NOT NULL,
                data TEXT NOT NULL,
                FOREIGN KEY (valuation_report_id) REFERENCES valuation_reports (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def valuate_frontend(self, asset_data: Dict[str, Any], 
                             methods: List[ValuationMethod] = None) -> ValuationReport:
        """Perform comprehensive frontend valuation"""
        
        if methods is None:
            methods = [ValuationMethod.HYBRID]
        
        # Create asset object
        frontend_asset = FrontendAsset(**asset_data)
        
        logger.info(f"Starting valuation for frontend {frontend_asset.id} using methods: {methods}")
        
        # Perform different valuation methods
        valuation_components = []
        
        for method in methods:
            if method == ValuationMethod.DCF:
                component = await self._dcf_valuation(frontend_asset)
            elif method == ValuationMethod.COMPARABLE:
                component = await self._comparable_valuation(frontend_asset)
            elif method == ValuationMethod.COST:
                component = await self._cost_based_valuation(frontend_asset)
            elif method == ValuationMethod.REVENUE_MULTIPLE:
                component = await self._revenue_multiple_valuation(frontend_asset)
            elif method == ValuationMethod.USER_MULTIPLE:
                component = await self._user_based_valuation(frontend_asset)
            elif method == ValuationMethod.TECH_STACK:
                component = await self._tech_stack_valuation(frontend_asset)
            elif method == ValuationMethod.DOMAIN_AUTHORITY:
                component = await self._domain_authority_valuation(frontend_asset)
            elif method == ValuationMethod.HYBRID:
                components = await self._hybrid_valuation(frontend_asset)
                valuation_components.extend(components)
                continue
            
            if component:
                valuation_components.append(component)
        
        # Calculate weighted average valuation
        base_valuation = self._calculate_weighted_valuation(valuation_components)
        
        # Risk assessment
        risk_assessment = await self._assess_risk(frontend_asset)
        risk_discount = risk_assessment["total_discount"]
        risk_adjusted_valuation = base_valuation * (1 - risk_discount)
        
        # Calculate valuation range (±25%)
        valuation_range_low = risk_adjusted_valuation * Decimal('0.75')
        valuation_range_high = risk_adjusted_valuation * Decimal('1.25')
        
        # Get market context
        market_context = await self._get_market_context(frontend_asset)
        
        # Create valuation report
        report = ValuationReport(
            id=f"VAL_{uuid.uuid4().hex[:8].upper()}",
            frontend_id=frontend_asset.id,
            valuator_id="system",
            base_valuation=base_valuation,
            risk_adjusted_valuation=risk_adjusted_valuation,
            valuation_range_low=valuation_range_low,
            valuation_range_high=valuation_range_high,
            valuation_components=valuation_components,
            primary_method=methods[0] if len(methods) == 1 else ValuationMethod.HYBRID,
            overall_risk_level=risk_assessment["risk_level"],
            risk_factors=risk_assessment["risk_factors"],
            risk_discount=risk_discount,
            market_conditions=market_context,
            comparable_transactions=await self._get_comparable_transactions(frontend_asset),
            valuation_date=datetime.now(),
            projected_growth_rate=frontend_asset.revenue_growth_rate,
            growth_assumptions={
                "revenue_growth": frontend_asset.revenue_growth_rate,
                "user_growth": frontend_asset.user_growth_rate,
                "market_expansion": 0.15
            }
        )
        
        # Store valuation report
        await self._store_valuation_report(report)
        
        logger.info(f"Completed valuation for {frontend_asset.id}: ${float(risk_adjusted_valuation):,.2f}")
        return report
    
    async def _dcf_valuation(self, asset: FrontendAsset) -> ValuationComponent:
        """Discounted Cash Flow valuation"""
        
        # Project future cash flows (5 years)
        years = 5
        discount_rate = 0.12  # 12% discount rate
        terminal_growth_rate = 0.03  # 3% terminal growth
        
        current_cash_flow = float(asset.annual_revenue - asset.maintenance_cost_monthly * 12)
        growth_rate = asset.revenue_growth_rate
        
        cash_flows = []
        for year in range(1, years + 1):
            future_cf = current_cash_flow * ((1 + growth_rate) ** year)
            discounted_cf = future_cf / ((1 + discount_rate) ** year)
            cash_flows.append(discounted_cf)
        
        # Terminal value
        terminal_cf = cash_flows[-1] * (1 + terminal_growth_rate)
        terminal_value = terminal_cf / (discount_rate - terminal_growth_rate)
        terminal_pv = terminal_value / ((1 + discount_rate) ** years)
        
        dcf_value = sum(cash_flows) + terminal_pv
        
        return ValuationComponent(
            component_name="Discounted Cash Flow",
            method=ValuationMethod.DCF,
            value=Decimal(str(max(0, dcf_value))),
            weight=0.35,
            confidence=0.8 if asset.annual_revenue > 0 else 0.4,
            assumptions={
                "discount_rate": discount_rate,
                "growth_rate": growth_rate,
                "terminal_growth": terminal_growth_rate,
                "projection_years": years
            },
            calculations={
                "sum_discounted_cf": sum(cash_flows),
                "terminal_value": terminal_pv,
                "total_dcf": dcf_value
            },
            notes=f"Based on projected cash flows over {years} years with {discount_rate:.1%} discount rate"
        )
    
    async def _comparable_valuation(self, asset: FrontendAsset) -> ValuationComponent:
        """Market comparables valuation"""
        
        # Get comparable transactions
        comparables = await self._get_comparable_transactions(asset)
        
        if not comparables:
            # Use industry averages
            category_mult = self.category_multipliers.get(asset.category, self.category_multipliers["default"])
            
            if asset.annual_revenue > 0:
                comp_value = float(asset.annual_revenue) * category_mult["revenue"]
            elif asset.monthly_active_users > 0:
                comp_value = asset.monthly_active_users * category_mult["user"]
            else:
                comp_value = 50000  # Minimum viable frontend value
        else:
            # Calculate weighted average from comparables
            total_weight = sum(comp.similarity_score for comp in comparables)
            if total_weight > 0:
                comp_value = sum(
                    float(comp.valuation) * comp.similarity_score 
                    for comp in comparables
                ) / total_weight
            else:
                comp_value = float(sum(comp.valuation for comp in comparables)) / len(comparables)
        
        return ValuationComponent(
            component_name="Market Comparables",
            method=ValuationMethod.COMPARABLE,
            value=Decimal(str(max(0, comp_value))),
            weight=0.25,
            confidence=0.9 if comparables else 0.6,
            assumptions={
                "comparables_count": len(comparables),
                "category_multiplier": self.category_multipliers.get(asset.category, {})
            },
            calculations={"comparable_value": comp_value},
            notes=f"Based on {len(comparables)} comparable transactions" if comparables 
                  else "Based on industry average multipliers"
        )
    
    async def _cost_based_valuation(self, asset: FrontendAsset) -> ValuationComponent:
        """Cost-based valuation approach"""
        
        # Development cost
        dev_cost = asset.development_time_hours * float(asset.hourly_rate)
        
        # Replacement cost (current market rates)
        current_market_rate = 75  # $75/hour current market rate
        replacement_cost = asset.development_time_hours * current_market_rate
        
        # Add premium for existing functionality
        functionality_premium = 1.5  # 50% premium for working system
        
        # Depreciation based on technical debt and age
        depreciation_factor = 1 - (asset.technical_debt_score * 0.3)
        
        cost_value = replacement_cost * functionality_premium * depreciation_factor
        
        return ValuationComponent(
            component_name="Cost-Based Approach",
            method=ValuationMethod.COST,
            value=Decimal(str(max(0, cost_value))),
            weight=0.15,
            confidence=0.7,
            assumptions={
                "original_dev_cost": dev_cost,
                "current_market_rate": current_market_rate,
                "functionality_premium": functionality_premium,
                "depreciation_factor": depreciation_factor
            },
            calculations={
                "replacement_cost": replacement_cost,
                "final_cost_value": cost_value
            },
            notes="Based on replacement cost with functionality premium and depreciation"
        )
    
    async def _revenue_multiple_valuation(self, asset: FrontendAsset) -> ValuationComponent:
        """Revenue multiple valuation"""
        
        if asset.annual_revenue == 0:
            return ValuationComponent(
                component_name="Revenue Multiple",
                method=ValuationMethod.REVENUE_MULTIPLE,
                value=Decimal('0'),
                weight=0.0,
                confidence=0.0,
                notes="No revenue data available"
            )
        
        # Get category-specific multiple
        category_mult = self.category_multipliers.get(
            asset.category, 
            self.category_multipliers["default"]
        )["revenue"]
        
        # Adjust multiple based on growth rate and profitability
        growth_adjustment = 1 + min(asset.revenue_growth_rate, 0.5)  # Cap at 50% bonus
        
        # Quality adjustment
        quality_score = (asset.performance_score + asset.code_quality_score) / 200
        quality_adjustment = 0.8 + (quality_score * 0.4)  # 0.8 to 1.2 range
        
        adjusted_multiple = category_mult * growth_adjustment * quality_adjustment
        revenue_value = float(asset.annual_revenue) * adjusted_multiple
        
        return ValuationComponent(
            component_name="Revenue Multiple",
            method=ValuationMethod.REVENUE_MULTIPLE,
            value=Decimal(str(revenue_value)),
            weight=0.3,
            confidence=0.85,
            assumptions={
                "base_multiple": category_mult,
                "growth_adjustment": growth_adjustment,
                "quality_adjustment": quality_adjustment,
                "final_multiple": adjusted_multiple
            },
            calculations={"revenue_value": revenue_value},
            notes=f"Annual revenue of ${float(asset.annual_revenue):,.2f} × {adjusted_multiple:.1f}x multiple"
        )
    
    async def _user_based_valuation(self, asset: FrontendAsset) -> ValuationComponent:
        """User-based valuation"""
        
        if asset.monthly_active_users == 0:
            return ValuationComponent(
                component_name="User-Based Valuation",
                method=ValuationMethod.USER_MULTIPLE,
                value=Decimal('0'),
                weight=0.0,
                confidence=0.0,
                notes="No user data available"
            )
        
        # Get category-specific per-user value
        category_mult = self.category_multipliers.get(
            asset.category,
            self.category_multipliers["default"]
        )["user"]
        
        # Adjust based on user engagement and LTV
        ltv_factor = min(float(asset.user_lifetime_value) / 50, 3.0)  # Cap at 3x
        engagement_factor = asset.performance_score / 100  # Performance as proxy for engagement
        
        adjusted_per_user_value = category_mult * (0.5 + ltv_factor * 0.3 + engagement_factor * 0.2)
        user_value = asset.monthly_active_users * adjusted_per_user_value
        
        return ValuationComponent(
            component_name="User-Based Valuation",
            method=ValuationMethod.USER_MULTIPLE,
            value=Decimal(str(user_value)),
            weight=0.2,
            confidence=0.75,
            assumptions={
                "base_per_user": category_mult,
                "ltv_factor": ltv_factor,
                "engagement_factor": engagement_factor,
                "adjusted_per_user": adjusted_per_user_value
            },
            calculations={"user_value": user_value},
            notes=f"{asset.monthly_active_users:,} MAU × ${adjusted_per_user_value:.2f} per user"
        )
    
    async def _tech_stack_valuation(self, asset: FrontendAsset) -> ValuationComponent:
        """Technology stack valuation"""
        
        # Base values for different frameworks/stacks
        framework_values = {
            "react": 1.2,
            "vue": 1.1,
            "angular": 1.15,
            "svelte": 1.0,
            "vanilla": 0.8,
            "legacy": 0.6
        }
        
        framework_multiplier = framework_values.get(asset.framework.lower(), 1.0)
        
        # Code quality impact
        code_quality_bonus = asset.code_quality_score / 100 * 0.3
        
        # Technical debt penalty
        tech_debt_penalty = asset.technical_debt_score * 0.2
        
        # Base tech value (minimum viable frontend)
        base_tech_value = 25000
        
        # Size/complexity bonus
        loc_bonus = min(asset.lines_of_code / 10000, 2.0)  # Up to 2x for large codebases
        
        tech_value = base_tech_value * framework_multiplier * (1 + code_quality_bonus + loc_bonus - tech_debt_penalty)
        
        return ValuationComponent(
            component_name="Technology Stack Value",
            method=ValuationMethod.TECH_STACK,
            value=Decimal(str(max(5000, tech_value))),  # Minimum $5k tech value
            weight=0.1,
            confidence=0.8,
            assumptions={
                "framework_multiplier": framework_multiplier,
                "code_quality_bonus": code_quality_bonus,
                "tech_debt_penalty": tech_debt_penalty,
                "loc_bonus": loc_bonus
            },
            calculations={"tech_value": tech_value},
            notes=f"Based on {asset.framework} framework with {asset.lines_of_code:,} LOC"
        )
    
    async def _domain_authority_valuation(self, asset: FrontendAsset) -> ValuationComponent:
        """Domain authority and SEO valuation"""
        
        # Domain authority value
        da_value = asset.domain_authority * 1000  # $1k per DA point
        
        # SEO score value
        seo_value = asset.seo_score * 500  # $500 per SEO score point
        
        # Brand/trademark value
        brand_value = 0
        if asset.has_trademark:
            brand_value += 10000
        
        total_domain_value = da_value + seo_value + brand_value
        
        return ValuationComponent(
            component_name="Domain Authority & SEO",
            method=ValuationMethod.DOMAIN_AUTHORITY,
            value=Decimal(str(total_domain_value)),
            weight=0.05,
            confidence=0.7,
            assumptions={
                "da_per_point": 1000,
                "seo_per_point": 500,
                "trademark_value": 10000 if asset.has_trademark else 0
            },
            calculations={
                "da_value": da_value,
                "seo_value": seo_value,
                "brand_value": brand_value
            },
            notes=f"DA: {asset.domain_authority}, SEO: {asset.seo_score}, Trademark: {asset.has_trademark}"
        )
    
    async def _hybrid_valuation(self, asset: FrontendAsset) -> List[ValuationComponent]:
        """Comprehensive hybrid valuation using multiple methods"""
        
        components = []
        
        # Always include cost-based as baseline
        components.append(await self._cost_based_valuation(asset))
        
        # Include revenue multiple if revenue exists
        if asset.annual_revenue > 0:
            components.append(await self._revenue_multiple_valuation(asset))
            components.append(await self._dcf_valuation(asset))
        
        # Include user-based if user data exists
        if asset.monthly_active_users > 0:
            components.append(await self._user_based_valuation(asset))
        
        # Always include tech stack and domain authority
        components.append(await self._tech_stack_valuation(asset))
        components.append(await self._domain_authority_valuation(asset))
        
        # Include market comparables
        components.append(await self._comparable_valuation(asset))
        
        return components
    
    def _calculate_weighted_valuation(self, components: List[ValuationComponent]) -> Decimal:
        """Calculate weighted average valuation from components"""
        
        if not components:
            return Decimal('0')
        
        total_weighted_value = Decimal('0')
        total_weight = 0.0
        
        for component in components:
            weighted_value = component.value * Decimal(str(component.weight * component.confidence))
            total_weighted_value += weighted_value
            total_weight += component.weight * component.confidence
        
        if total_weight == 0:
            return Decimal('0')
        
        return (total_weighted_value / Decimal(str(total_weight))).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
    
    async def _assess_risk(self, asset: FrontendAsset) -> Dict[str, Any]:
        """Comprehensive risk assessment"""
        
        risk_factors = []
        total_discount = 0.0
        
        # Technical debt risk
        if asset.technical_debt_score > 0.7:
            risk_factors.append({
                "factor": "high_technical_debt",
                "impact": self.risk_factors["high_technical_debt"],
                "description": f"High technical debt score: {asset.technical_debt_score:.2f}"
            })
            total_discount += self.risk_factors["high_technical_debt"]
        
        # Framework/technology risk
        deprecated_frameworks = ["angularjs", "knockout", "backbone"]
        if asset.framework.lower() in deprecated_frameworks:
            risk_factors.append({
                "factor": "deprecated_framework",
                "impact": self.risk_factors["deprecated_framework"],
                "description": f"Using deprecated framework: {asset.framework}"
            })
            total_discount += self.risk_factors["deprecated_framework"]
        
        # Documentation risk
        if asset.documentation_completeness < 0.5:
            risk_factors.append({
                "factor": "no_documentation",
                "impact": self.risk_factors["no_documentation"],
                "description": f"Poor documentation: {asset.documentation_completeness:.1%} complete"
            })
            total_discount += self.risk_factors["no_documentation"]
        
        # Testing risk
        if asset.test_coverage < 0.3:
            risk_factors.append({
                "factor": "no_tests",
                "impact": self.risk_factors["no_tests"],
                "description": f"Low test coverage: {asset.test_coverage:.1%}"
            })
            total_discount += self.risk_factors["no_tests"]
        
        # Performance risk
        if asset.performance_score < 50:
            risk_factors.append({
                "factor": "performance_issues",
                "impact": self.risk_factors["performance_issues"],
                "description": f"Poor performance score: {asset.performance_score}"
            })
            total_discount += self.risk_factors["performance_issues"]
        
        # Determine overall risk level
        if total_discount >= 0.4:
            risk_level = RiskLevel.VERY_HIGH
        elif total_discount >= 0.25:
            risk_level = RiskLevel.HIGH
        elif total_discount >= 0.1:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW
        
        return {
            "risk_level": risk_level,
            "total_discount": min(total_discount, 0.6),  # Cap at 60% discount
            "risk_factors": risk_factors
        }
    
    async def _get_market_context(self, asset: FrontendAsset) -> Dict[str, Any]:
        """Get market context and conditions"""
        
        return {
            "market_sentiment": "positive",  # Would integrate with market data APIs
            "category_growth": 0.15,
            "competition_level": "medium",
            "technology_trend": "stable" if asset.framework in ["react", "vue", "angular"] else "declining",
            "funding_environment": "moderate",
            "acquisition_activity": "high"
        }
    
    async def _get_comparable_transactions(self, asset: FrontendAsset) -> List[MarketComparable]:
        """Get comparable transactions from database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Find comparables with similar characteristics
        cursor.execute('''
            SELECT data FROM market_comparables 
            WHERE category = ? OR framework = ?
            ORDER BY created_at DESC 
            LIMIT 10
        ''', (asset.category, asset.framework))
        
        results = cursor.fetchall()
        conn.close()
        
        comparables = []
        for result in results:
            comp_data = json.loads(result[0])
            comparable = MarketComparable(**comp_data)
            
            # Calculate similarity score
            similarity = self._calculate_similarity(asset, comparable)
            comparable.similarity_score = similarity
            
            comparables.append(comparable)
        
        # Sort by similarity and return top 5
        comparables.sort(key=lambda x: x.similarity_score, reverse=True)
        return comparables[:5]
    
    def _calculate_similarity(self, asset: FrontendAsset, comparable: MarketComparable) -> float:
        """Calculate similarity score between assets"""
        
        similarity = 0.0
        
        # Category similarity (40% weight)
        if asset.category == comparable.category:
            similarity += 0.4
        
        # Framework similarity (30% weight)
        if asset.framework == comparable.framework:
            similarity += 0.3
        
        # Size similarity (20% weight)
        if comparable.user_count > 0 and asset.monthly_active_users > 0:
            size_ratio = min(asset.monthly_active_users, comparable.user_count) / max(asset.monthly_active_users, comparable.user_count)
            similarity += 0.2 * size_ratio
        
        # Revenue similarity (10% weight)
        if comparable.revenue > 0 and asset.annual_revenue > 0:
            revenue_ratio = min(float(asset.annual_revenue), float(comparable.revenue)) / max(float(asset.annual_revenue), float(comparable.revenue))
            similarity += 0.1 * revenue_ratio
        
        return min(similarity, 1.0)
    
    async def _store_valuation_report(self, report: ValuationReport):
        """Store valuation report in database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Store main report
        cursor.execute('''
            INSERT INTO valuation_reports 
            (id, frontend_id, valuator_id, base_valuation, risk_adjusted_valuation, 
             primary_method, overall_risk_level, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            report.id, report.frontend_id, report.valuator_id,
            float(report.base_valuation), float(report.risk_adjusted_valuation),
            report.primary_method.value, report.overall_risk_level.value,
            report.model_dump_json()
        ))
        
        # Store components
        for component in report.valuation_components:
            component_id = f"COMP_{uuid.uuid4().hex[:8].upper()}"
            cursor.execute('''
                INSERT INTO valuation_components 
                (id, valuation_report_id, component_name, method, value, weight, confidence, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                component_id, report.id, component.component_name,
                component.method.value, float(component.value),
                component.weight, component.confidence, component.model_dump_json()
            ))
        
        conn.commit()
        conn.close()
    
    async def get_valuation_history(self, frontend_id: str) -> List[ValuationReport]:
        """Get valuation history for frontend"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT data FROM valuation_reports 
            WHERE frontend_id = ? 
            ORDER BY valuation_date DESC
        ''', (frontend_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [ValuationReport(**json.loads(result[0])) for result in results]
    
    async def add_market_comparable(self, comparable_data: Dict[str, Any]) -> MarketComparable:
        """Add new market comparable transaction"""
        
        comparable = MarketComparable(**comparable_data)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO market_comparables 
            (id, name, framework, category, revenue, user_count, valuation, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            comparable.id, comparable.name, comparable.framework,
            comparable.category, float(comparable.revenue),
            comparable.user_count, float(comparable.valuation),
            comparable.model_dump_json()
        ))
        
        conn.commit()
        conn.close()
        
        return comparable

# Global instance
frontend_valuation_manager = FrontendValuationManager()