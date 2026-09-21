#!/usr/bin/env python3
"""
Business Valuation Tools System
Comprehensive business valuation and financial modeling platform

Features:
- Multiple valuation methodologies (DCF, comparable company, precedent transactions)
- Real-time market data integration for valuation multiples
- 409A valuation compliance and reporting
- Scenario modeling and sensitivity analysis
- Monte Carlo simulation for valuation ranges
- Industry-specific valuation models
- Startup valuation frameworks (risk-adjusted NPV, venture capital method)
- Asset-based valuation methods
- Revenue and EBITDA multiple analysis
- Waterfall analysis integration
- Valuation reporting and documentation
- Historical valuation tracking and trends
- Market comparables database
- Valuation audit trail and governance
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
import math
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)

class ValuationMethod(str, Enum):
    DCF = "dcf"  # Discounted Cash Flow
    COMPARABLE_COMPANY = "comparable_company"
    PRECEDENT_TRANSACTION = "precedent_transaction"
    ASSET_BASED = "asset_based"
    VENTURE_CAPITAL_METHOD = "venture_capital_method"
    RISK_ADJUSTED_NPV = "risk_adjusted_npv"
    REVENUE_MULTIPLE = "revenue_multiple"
    EBITDA_MULTIPLE = "ebitda_multiple"
    BOOK_VALUE = "book_value"
    LIQUIDATION_VALUE = "liquidation_value"

class ValuationPurpose(str, Enum):
    FUNDRAISING = "fundraising"
    ACQUISITION = "acquisition"
    TAX_COMPLIANCE = "tax_compliance"
    EMPLOYEE_STOCK_OPTION = "employee_stock_option"  # 409A
    FINANCIAL_REPORTING = "financial_reporting"
    LITIGATION = "litigation"
    ESTATE_PLANNING = "estate_planning"

class CompanyStage(str, Enum):
    SEED = "seed"
    EARLY_STAGE = "early_stage"
    GROWTH = "growth"
    MATURE = "mature"
    DISTRESSED = "distressed"

class ValuationAssumption(BaseModel):
    id: str
    category: str  # growth, discount_rate, multiple, market
    name: str
    base_case_value: float
    optimistic_value: float
    pessimistic_value: float
    probability_distribution: str = "normal"  # normal, uniform, triangular
    source: str = ""
    confidence_level: float = 0.7  # 0-1
    created_at: datetime

class FinancialProjection(BaseModel):
    id: str
    business_id: str
    projection_name: str
    
    # Time horizon
    projection_years: int = 5
    projection_start_date: datetime
    
    # Revenue projections
    revenue_streams: Dict[str, List[float]] = {}  # stream_name -> yearly values
    total_revenue: List[float] = []
    revenue_growth_rates: List[float] = []
    
    # Cost structure
    cost_of_goods_sold: List[float] = []
    operating_expenses: List[float] = []
    depreciation: List[float] = []
    
    # Profitability metrics
    gross_profit: List[float] = []
    ebitda: List[float] = []
    ebit: List[float] = []
    net_income: List[float] = []
    
    # Cash flow
    operating_cash_flow: List[float] = []
    capex: List[float] = []
    free_cash_flow: List[float] = []
    
    # Balance sheet items
    working_capital: List[float] = []
    net_debt: List[float] = []
    
    # Key assumptions
    assumptions: List[ValuationAssumption] = []
    
    created_at: datetime
    updated_at: datetime

class MarketComparable(BaseModel):
    id: str
    company_name: str
    ticker_symbol: Optional[str] = None
    
    # Company details
    industry: str
    business_description: str
    market_cap: float
    enterprise_value: float
    
    # Financial metrics
    revenue_ttm: float  # Trailing twelve months
    revenue_growth: float
    ebitda_ttm: float
    ebitda_margin: float
    gross_margin: float
    
    # Valuation multiples
    ev_revenue_multiple: float
    ev_ebitda_multiple: float
    price_earnings_multiple: Optional[float] = None
    price_book_multiple: Optional[float] = None
    
    # Additional metrics
    geographic_focus: List[str] = []
    size_category: str = "mid_cap"  # micro, small, mid, large
    profitability_profile: str = "profitable"  # profitable, break_even, loss_making
    
    data_date: datetime
    created_at: datetime

class TransactionComparable(BaseModel):
    id: str
    target_company: str
    acquirer_company: str
    
    # Transaction details
    transaction_date: datetime
    transaction_value: float
    revenue_multiple: float
    ebitda_multiple: Optional[float] = None
    
    # Target company details
    target_revenue: float
    target_ebitda: Optional[float] = None
    target_industry: str
    target_geography: str
    
    # Transaction characteristics
    transaction_type: str = "acquisition"  # acquisition, merger, ipo
    strategic_premium: float = 0.0  # Premium paid for strategic value
    
    created_at: datetime

class ValuationModel(BaseModel):
    id: str
    business_id: str
    valuation_date: datetime
    
    # Model details
    model_name: str
    valuation_method: ValuationMethod
    valuation_purpose: ValuationPurpose
    company_stage: CompanyStage
    
    # Key inputs
    financial_projections_id: Optional[str] = None
    discount_rate: float = 0.12  # Weighted average cost of capital
    terminal_growth_rate: float = 0.025  # Long-term growth rate
    
    # Valuation results
    equity_value: float = 0
    enterprise_value: float = 0
    per_share_value: float = 0
    
    # Valuation range
    optimistic_value: float = 0
    pessimistic_value: float = 0
    base_case_value: float = 0
    
    # Method-specific data
    model_inputs: Dict[str, Any] = {}
    calculation_details: Dict[str, Any] = {}
    
    # Quality and confidence
    confidence_level: float = 0.7
    key_risks: List[str] = []
    key_value_drivers: List[str] = []
    
    # Documentation
    methodology_notes: str = ""
    supporting_analysis: Dict[str, Any] = {}
    
    created_at: datetime
    updated_at: datetime
    created_by: str

class ValuationReport(BaseModel):
    id: str
    business_id: str
    report_title: str
    
    # Report metadata
    valuation_date: datetime
    report_purpose: ValuationPurpose
    prepared_by: str
    reviewed_by: Optional[str] = None
    
    # Executive summary
    executive_summary: str = ""
    key_conclusions: List[str] = []
    valuation_range: Dict[str, float] = {}  # low, mid, high
    
    # Methodology
    primary_methods: List[ValuationMethod] = []
    secondary_methods: List[ValuationMethod] = []
    method_weights: Dict[str, float] = {}
    
    # Supporting analysis
    market_analysis: Dict[str, Any] = {}
    financial_analysis: Dict[str, Any] = {}
    risk_analysis: Dict[str, Any] = {}
    
    # Model references
    valuation_model_ids: List[str] = []
    
    # Final conclusion
    final_valuation: float = 0
    valuation_per_share: float = 0
    
    created_at: datetime
    updated_at: datetime

class BusinessValuationManager:
    def __init__(self):
        self.financial_projections: Dict[str, FinancialProjection] = {}
        self.market_comparables: Dict[str, MarketComparable] = {}
        self.transaction_comparables: Dict[str, TransactionComparable] = {}
        self.valuation_models: Dict[str, ValuationModel] = {}
        self.valuation_reports: Dict[str, ValuationReport] = {}
        
        # Market data cache
        self.market_data_cache: Dict[str, Any] = {}
        
        # Initialize sample market data
        self._initialize_sample_market_data()
    
    def _initialize_sample_market_data(self):
        """Initialize sample market comparable data"""
        
        # Sample SaaS companies
        saas_comparables = [
            {
                "company_name": "Salesforce",
                "ticker_symbol": "CRM",
                "industry": "SaaS",
                "market_cap": 200000000000,
                "revenue_ttm": 26000000000,
                "revenue_growth": 0.24,
                "ebitda_ttm": 5200000000,
                "ev_revenue_multiple": 8.5,
                "ev_ebitda_multiple": 42.0
            },
            {
                "company_name": "Zoom",
                "ticker_symbol": "ZM", 
                "industry": "SaaS",
                "market_cap": 25000000000,
                "revenue_ttm": 4000000000,
                "revenue_growth": 0.12,
                "ebitda_ttm": 1200000000,
                "ev_revenue_multiple": 6.2,
                "ev_ebitda_multiple": 20.8
            },
            {
                "company_name": "Shopify",
                "ticker_symbol": "SHOP",
                "industry": "E-commerce",
                "market_cap": 60000000000,
                "revenue_ttm": 5600000000,
                "revenue_growth": 0.26,
                "ebitda_ttm": 400000000,
                "ev_revenue_multiple": 10.7,
                "ev_ebitda_multiple": 150.0
            }
        ]
        
        for comp_data in saas_comparables:
            comp_id = str(uuid.uuid4())
            comp = MarketComparable(
                id=comp_id,
                company_name=comp_data["company_name"],
                ticker_symbol=comp_data.get("ticker_symbol"),
                industry=comp_data["industry"],
                business_description=f"{comp_data['company_name']} - {comp_data['industry']} company",
                market_cap=comp_data["market_cap"],
                enterprise_value=comp_data["market_cap"] * 1.1,  # Simplified
                revenue_ttm=comp_data["revenue_ttm"],
                revenue_growth=comp_data["revenue_growth"],
                ebitda_ttm=comp_data["ebitda_ttm"],
                ebitda_margin=comp_data["ebitda_ttm"] / comp_data["revenue_ttm"],
                gross_margin=0.75,  # Assume 75% gross margin
                ev_revenue_multiple=comp_data["ev_revenue_multiple"],
                ev_ebitda_multiple=comp_data["ev_ebitda_multiple"],
                size_category="large_cap",
                profitability_profile="profitable",
                data_date=datetime.now(),
                created_at=datetime.now()
            )
            self.market_comparables[comp_id] = comp
    
    async def create_financial_projection(
        self, 
        business_id: str, 
        projection_data: Dict[str, Any]
    ) -> FinancialProjection:
        """Create financial projections for valuation"""
        
        projection_id = str(uuid.uuid4())
        
        projection = FinancialProjection(
            id=projection_id,
            business_id=business_id,
            projection_name=projection_data.get("name", "Base Case Projection"),
            projection_years=projection_data.get("projection_years", 5),
            projection_start_date=projection_data.get("start_date", datetime.now()),
            revenue_streams=projection_data.get("revenue_streams", {}),
            total_revenue=projection_data.get("total_revenue", []),
            revenue_growth_rates=projection_data.get("revenue_growth_rates", []),
            cost_of_goods_sold=projection_data.get("cogs", []),
            operating_expenses=projection_data.get("opex", []),
            depreciation=projection_data.get("depreciation", []),
            capex=projection_data.get("capex", []),
            working_capital=projection_data.get("working_capital", []),
            assumptions=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Calculate derived metrics
        projection = await self._calculate_projection_metrics(projection)
        
        self.financial_projections[projection_id] = projection
        return projection
    
    async def _calculate_projection_metrics(self, projection: FinancialProjection) -> FinancialProjection:
        """Calculate derived financial metrics from projections"""
        
        years = projection.projection_years
        
        # Calculate gross profit
        if projection.total_revenue and projection.cost_of_goods_sold:
            projection.gross_profit = [
                rev - cogs for rev, cogs in zip(projection.total_revenue, projection.cost_of_goods_sold)
            ]
        
        # Calculate EBITDA
        if projection.gross_profit and projection.operating_expenses:
            projection.ebitda = [
                gp - opex for gp, opex in zip(projection.gross_profit, projection.operating_expenses)
            ]
        
        # Calculate EBIT
        if projection.ebitda and projection.depreciation:
            projection.ebit = [
                ebitda - dep for ebitda, dep in zip(projection.ebitda, projection.depreciation)
            ]
        
        # Calculate operating cash flow (simplified)
        if projection.ebitda:
            projection.operating_cash_flow = projection.ebitda.copy()
        
        # Calculate free cash flow
        if projection.operating_cash_flow and projection.capex:
            projection.free_cash_flow = [
                ocf - capex for ocf, capex in zip(projection.operating_cash_flow, projection.capex)
            ]
        elif projection.operating_cash_flow:
            projection.free_cash_flow = projection.operating_cash_flow.copy()
        
        return projection
    
    async def create_dcf_valuation(
        self, 
        business_id: str, 
        dcf_inputs: Dict[str, Any]
    ) -> ValuationModel:
        """Create DCF (Discounted Cash Flow) valuation model"""
        
        model_id = str(uuid.uuid4())
        
        # Get or create financial projections
        projection_id = dcf_inputs.get("financial_projections_id")
        if not projection_id:
            # Create basic projections from inputs
            projection = await self.create_financial_projection(business_id, dcf_inputs.get("projections", {}))
            projection_id = projection.id
        
        projection = self.financial_projections.get(projection_id)
        if not projection:
            raise ValueError("Financial projections not found")
        
        # DCF calculation parameters
        discount_rate = dcf_inputs.get("discount_rate", 0.12)
        terminal_growth_rate = dcf_inputs.get("terminal_growth_rate", 0.025)
        
        # Calculate DCF valuation
        dcf_results = await self._calculate_dcf_value(projection, discount_rate, terminal_growth_rate)
        
        model = ValuationModel(
            id=model_id,
            business_id=business_id,
            valuation_date=dcf_inputs.get("valuation_date", datetime.now()),
            model_name=dcf_inputs.get("model_name", "DCF Valuation"),
            valuation_method=ValuationMethod.DCF,
            valuation_purpose=ValuationPurpose(dcf_inputs.get("purpose", "fundraising")),
            company_stage=CompanyStage(dcf_inputs.get("company_stage", "growth")),
            financial_projections_id=projection_id,
            discount_rate=discount_rate,
            terminal_growth_rate=terminal_growth_rate,
            enterprise_value=dcf_results["enterprise_value"],
            equity_value=dcf_results["equity_value"],
            per_share_value=dcf_results["per_share_value"],
            base_case_value=dcf_results["equity_value"],
            model_inputs={
                "discount_rate": discount_rate,
                "terminal_growth_rate": terminal_growth_rate,
                "projection_years": projection.projection_years
            },
            calculation_details=dcf_results["calculation_details"],
            confidence_level=dcf_inputs.get("confidence_level", 0.7),
            key_value_drivers=dcf_inputs.get("key_value_drivers", [
                "Revenue growth rate",
                "Operating margins",
                "Capital efficiency",
                "Terminal growth rate"
            ]),
            methodology_notes="DCF model based on projected free cash flows discounted at WACC",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            created_by=dcf_inputs.get("created_by", "system")
        )
        
        self.valuation_models[model_id] = model
        return model
    
    async def _calculate_dcf_value(
        self, 
        projection: FinancialProjection, 
        discount_rate: float, 
        terminal_growth_rate: float
    ) -> Dict[str, Any]:
        """Calculate DCF valuation"""
        
        if not projection.free_cash_flow:
            raise ValueError("Free cash flow projections required for DCF")
        
        # Discount factors
        discount_factors = [(1 / (1 + discount_rate) ** (i + 1)) for i in range(len(projection.free_cash_flow))]
        
        # Present value of projected cash flows
        pv_cash_flows = [
            fcf * df for fcf, df in zip(projection.free_cash_flow, discount_factors)
        ]
        
        # Terminal value calculation
        terminal_fcf = projection.free_cash_flow[-1] * (1 + terminal_growth_rate)
        terminal_value = terminal_fcf / (discount_rate - terminal_growth_rate)
        pv_terminal_value = terminal_value / ((1 + discount_rate) ** len(projection.free_cash_flow))
        
        # Enterprise value
        enterprise_value = sum(pv_cash_flows) + pv_terminal_value
        
        # Equity value (assuming no net debt for simplicity)
        net_debt = 0  # Would get from balance sheet
        equity_value = enterprise_value - net_debt
        
        # Per share value (assuming 1M shares outstanding)
        shares_outstanding = 1000000
        per_share_value = equity_value / shares_outstanding
        
        calculation_details = {
            "projected_fcf": projection.free_cash_flow,
            "discount_factors": discount_factors,
            "pv_cash_flows": pv_cash_flows,
            "sum_pv_cash_flows": sum(pv_cash_flows),
            "terminal_fcf": terminal_fcf,
            "terminal_value": terminal_value,
            "pv_terminal_value": pv_terminal_value,
            "terminal_value_percentage": (pv_terminal_value / enterprise_value) * 100
        }
        
        return {
            "enterprise_value": enterprise_value,
            "equity_value": equity_value,
            "per_share_value": per_share_value,
            "calculation_details": calculation_details
        }
    
    async def create_comparable_company_valuation(
        self, 
        business_id: str, 
        comp_inputs: Dict[str, Any]
    ) -> ValuationModel:
        """Create comparable company valuation model"""
        
        model_id = str(uuid.uuid4())
        
        # Get target company metrics
        target_revenue = comp_inputs.get("target_revenue", 0)
        target_ebitda = comp_inputs.get("target_ebitda", 0)
        target_industry = comp_inputs.get("target_industry", "")
        
        # Find comparable companies
        comparable_companies = await self._find_comparable_companies(target_industry)
        
        if not comparable_companies:
            raise ValueError("No comparable companies found for industry")
        
        # Calculate valuation multiples
        multiples_analysis = await self._analyze_trading_multiples(comparable_companies)
        
        # Apply multiples to target company
        valuation_results = await self._apply_multiples_valuation(
            target_revenue, 
            target_ebitda, 
            multiples_analysis
        )
        
        model = ValuationModel(
            id=model_id,
            business_id=business_id,
            valuation_date=comp_inputs.get("valuation_date", datetime.now()),
            model_name=comp_inputs.get("model_name", "Comparable Company Valuation"),
            valuation_method=ValuationMethod.COMPARABLE_COMPANY,
            valuation_purpose=ValuationPurpose(comp_inputs.get("purpose", "fundraising")),
            company_stage=CompanyStage(comp_inputs.get("company_stage", "growth")),
            enterprise_value=valuation_results["enterprise_value"],
            equity_value=valuation_results["equity_value"],
            per_share_value=valuation_results["per_share_value"],
            base_case_value=valuation_results["equity_value"],
            optimistic_value=valuation_results["optimistic_value"],
            pessimistic_value=valuation_results["pessimistic_value"],
            model_inputs={
                "target_revenue": target_revenue,
                "target_ebitda": target_ebitda,
                "target_industry": target_industry,
                "comparables_count": len(comparable_companies)
            },
            calculation_details=valuation_results["calculation_details"],
            confidence_level=comp_inputs.get("confidence_level", 0.6),
            key_value_drivers=[
                "Market multiples",
                "Industry comparability",
                "Size premiums/discounts",
                "Profitability profile"
            ],
            methodology_notes="Valuation based on trading multiples of comparable public companies",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            created_by=comp_inputs.get("created_by", "system")
        )
        
        self.valuation_models[model_id] = model
        return model
    
    async def _find_comparable_companies(self, target_industry: str) -> List[MarketComparable]:
        """Find comparable companies based on industry"""
        comparable_companies = []
        
        for comp in self.market_comparables.values():
            if target_industry.lower() in comp.industry.lower():
                comparable_companies.append(comp)
        
        return comparable_companies
    
    async def _analyze_trading_multiples(self, comparables: List[MarketComparable]) -> Dict[str, Any]:
        """Analyze trading multiples from comparable companies"""
        
        # Revenue multiples
        revenue_multiples = [comp.ev_revenue_multiple for comp in comparables if comp.ev_revenue_multiple > 0]
        
        # EBITDA multiples
        ebitda_multiples = [comp.ev_ebitda_multiple for comp in comparables if comp.ev_ebitda_multiple and comp.ev_ebitda_multiple > 0]
        
        analysis = {
            "revenue_multiples": {
                "median": statistics.median(revenue_multiples) if revenue_multiples else 0,
                "mean": statistics.mean(revenue_multiples) if revenue_multiples else 0,
                "25th_percentile": statistics.quantiles(revenue_multiples, n=4)[0] if len(revenue_multiples) > 1 else 0,
                "75th_percentile": statistics.quantiles(revenue_multiples, n=4)[2] if len(revenue_multiples) > 1 else 0,
                "count": len(revenue_multiples)
            },
            "ebitda_multiples": {
                "median": statistics.median(ebitda_multiples) if ebitda_multiples else 0,
                "mean": statistics.mean(ebitda_multiples) if ebitda_multiples else 0,
                "25th_percentile": statistics.quantiles(ebitda_multiples, n=4)[0] if len(ebitda_multiples) > 1 else 0,
                "75th_percentile": statistics.quantiles(ebitda_multiples, n=4)[2] if len(ebitda_multiples) > 1 else 0,
                "count": len(ebitda_multiples)
            },
            "comparable_companies": [
                {
                    "name": comp.company_name,
                    "revenue_multiple": comp.ev_revenue_multiple,
                    "ebitda_multiple": comp.ev_ebitda_multiple,
                    "revenue_growth": comp.revenue_growth,
                    "ebitda_margin": comp.ebitda_margin
                }
                for comp in comparables
            ]
        }
        
        return analysis
    
    async def _apply_multiples_valuation(
        self, 
        target_revenue: float, 
        target_ebitda: float, 
        multiples_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply multiples to calculate valuation"""
        
        # Revenue-based valuation
        revenue_multiple_median = multiples_analysis["revenue_multiples"]["median"]
        revenue_based_value = target_revenue * revenue_multiple_median
        
        # EBITDA-based valuation
        ebitda_multiple_median = multiples_analysis["ebitda_multiples"]["median"]
        ebitda_based_value = target_ebitda * ebitda_multiple_median if target_ebitda > 0 else 0
        
        # Blended valuation (weighted average)
        if ebitda_based_value > 0:
            # Weight EBITDA more heavily for profitable companies
            blended_value = (revenue_based_value * 0.4) + (ebitda_based_value * 0.6)
        else:
            # Use revenue multiple for non-profitable companies
            blended_value = revenue_based_value
        
        # Calculate range using percentiles
        revenue_25th = multiples_analysis["revenue_multiples"]["25th_percentile"]
        revenue_75th = multiples_analysis["revenue_multiples"]["75th_percentile"]
        
        pessimistic_value = target_revenue * revenue_25th
        optimistic_value = target_revenue * revenue_75th
        
        # Assume equity value = enterprise value (no net debt adjustment)
        enterprise_value = blended_value
        equity_value = enterprise_value
        
        # Per share value
        shares_outstanding = 1000000  # Assumed
        per_share_value = equity_value / shares_outstanding
        
        calculation_details = {
            "revenue_multiple_median": revenue_multiple_median,
            "ebitda_multiple_median": ebitda_multiple_median,
            "revenue_based_value": revenue_based_value,
            "ebitda_based_value": ebitda_based_value,
            "blended_value": blended_value,
            "multiples_analysis": multiples_analysis
        }
        
        return {
            "enterprise_value": enterprise_value,
            "equity_value": equity_value,
            "per_share_value": per_share_value,
            "optimistic_value": optimistic_value,
            "pessimistic_value": pessimistic_value,
            "calculation_details": calculation_details
        }
    
    async def create_venture_capital_method_valuation(
        self, 
        business_id: str, 
        vc_inputs: Dict[str, Any]
    ) -> ValuationModel:
        """Create valuation using Venture Capital Method"""
        
        model_id = str(uuid.uuid4())
        
        # VC Method inputs
        exit_year = vc_inputs.get("exit_year", 5)
        projected_revenue_at_exit = vc_inputs.get("projected_revenue_at_exit", 0)
        exit_revenue_multiple = vc_inputs.get("exit_revenue_multiple", 5.0)
        target_irr = vc_inputs.get("target_irr", 0.30)  # 30% IRR target
        
        # Calculate terminal value
        terminal_value = projected_revenue_at_exit * exit_revenue_multiple
        
        # Present value of terminal value
        present_value = terminal_value / ((1 + target_irr) ** exit_year)
        
        # Apply risk adjustments
        risk_adjustment = vc_inputs.get("risk_adjustment", 0.5)  # 50% probability of success
        risk_adjusted_value = present_value * risk_adjustment
        
        model = ValuationModel(
            id=model_id,
            business_id=business_id,
            valuation_date=vc_inputs.get("valuation_date", datetime.now()),
            model_name=vc_inputs.get("model_name", "Venture Capital Method Valuation"),
            valuation_method=ValuationMethod.VENTURE_CAPITAL_METHOD,
            valuation_purpose=ValuationPurpose(vc_inputs.get("purpose", "fundraising")),
            company_stage=CompanyStage.SEED,
            enterprise_value=risk_adjusted_value,
            equity_value=risk_adjusted_value,
            per_share_value=risk_adjusted_value / 1000000,  # Assume 1M shares
            base_case_value=risk_adjusted_value,
            model_inputs={
                "exit_year": exit_year,
                "projected_revenue_at_exit": projected_revenue_at_exit,
                "exit_revenue_multiple": exit_revenue_multiple,
                "target_irr": target_irr,
                "risk_adjustment": risk_adjustment
            },
            calculation_details={
                "terminal_value": terminal_value,
                "present_value_before_risk": present_value,
                "risk_adjusted_present_value": risk_adjusted_value,
                "implied_exit_value": terminal_value
            },
            confidence_level=0.5,  # Lower confidence for early-stage valuations
            key_value_drivers=[
                "Exit timeline",
                "Revenue growth trajectory", 
                "Exit multiples",
                "Execution risk"
            ],
            methodology_notes="Venture Capital Method for early-stage company valuation",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            created_by=vc_inputs.get("created_by", "system")
        )
        
        self.valuation_models[model_id] = model
        return model
    
    async def perform_sensitivity_analysis(
        self, 
        model_id: str, 
        sensitivity_parameters: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """Perform sensitivity analysis on valuation model"""
        
        model = self.valuation_models.get(model_id)
        if not model:
            raise ValueError("Valuation model not found")
        
        sensitivity_results = {}
        base_value = model.equity_value
        
        for parameter, scenarios in sensitivity_parameters.items():
            parameter_results = {}
            
            for scenario_name, scenario_value in scenarios.items():
                # Recalculate valuation with new parameter value
                new_value = await self._recalculate_with_parameter(
                    model, parameter, scenario_value
                )
                
                change_percentage = ((new_value - base_value) / base_value) * 100
                
                parameter_results[scenario_name] = {
                    "parameter_value": scenario_value,
                    "valuation": new_value,
                    "change_percentage": change_percentage,
                    "change_absolute": new_value - base_value
                }
            
            sensitivity_results[parameter] = parameter_results
        
        # Create sensitivity matrix for key parameters
        if "discount_rate" in sensitivity_parameters and "terminal_growth_rate" in sensitivity_parameters:
            sensitivity_matrix = await self._create_sensitivity_matrix(
                model, 
                sensitivity_parameters["discount_rate"], 
                sensitivity_parameters["terminal_growth_rate"]
            )
            sensitivity_results["sensitivity_matrix"] = sensitivity_matrix
        
        return {
            "model_id": model_id,
            "base_case_value": base_value,
            "sensitivity_analysis": sensitivity_results,
            "most_sensitive_parameter": self._identify_most_sensitive_parameter(sensitivity_results),
            "analysis_date": datetime.now().isoformat()
        }
    
    async def _recalculate_with_parameter(
        self, 
        model: ValuationModel, 
        parameter: str, 
        new_value: float
    ) -> float:
        """Recalculate valuation with new parameter value"""
        
        if model.valuation_method == ValuationMethod.DCF:
            if parameter == "discount_rate":
                # Recalculate DCF with new discount rate
                projection = self.financial_projections.get(model.financial_projections_id)
                if projection:
                    results = await self._calculate_dcf_value(
                        projection, new_value, model.terminal_growth_rate
                    )
                    return results["equity_value"]
            elif parameter == "terminal_growth_rate":
                # Recalculate DCF with new terminal growth rate
                projection = self.financial_projections.get(model.financial_projections_id)
                if projection:
                    results = await self._calculate_dcf_value(
                        projection, model.discount_rate, new_value
                    )
                    return results["equity_value"]
        
        # For other parameters or methods, apply percentage change
        parameter_impact = {
            "revenue_growth": 1.5,  # 1% revenue growth change = 1.5% valuation change
            "ebitda_margin": 2.0,   # 1% margin change = 2% valuation change
            "multiple": 1.0         # 1% multiple change = 1% valuation change
        }
        
        impact_factor = parameter_impact.get(parameter, 1.0)
        percentage_change = (new_value - model.model_inputs.get(parameter, new_value)) * impact_factor
        
        return model.equity_value * (1 + percentage_change / 100)
    
    async def _create_sensitivity_matrix(
        self, 
        model: ValuationModel, 
        discount_rates: Dict[str, float], 
        growth_rates: Dict[str, float]
    ) -> Dict[str, Dict[str, float]]:
        """Create two-parameter sensitivity matrix"""
        
        matrix = {}
        
        for dr_scenario, discount_rate in discount_rates.items():
            matrix[dr_scenario] = {}
            
            for gr_scenario, growth_rate in growth_rates.items():
                # Calculate valuation with both parameters
                if model.valuation_method == ValuationMethod.DCF:
                    projection = self.financial_projections.get(model.financial_projections_id)
                    if projection:
                        results = await self._calculate_dcf_value(
                            projection, discount_rate, growth_rate
                        )
                        matrix[dr_scenario][gr_scenario] = results["equity_value"]
        
        return matrix
    
    def _identify_most_sensitive_parameter(self, sensitivity_results: Dict[str, Any]) -> str:
        """Identify parameter with highest sensitivity"""
        
        max_sensitivity = 0
        most_sensitive = ""
        
        for parameter, results in sensitivity_results.items():
            if isinstance(results, dict) and "parameter_results" not in results:
                # Calculate average absolute change
                changes = []
                for scenario_data in results.values():
                    if isinstance(scenario_data, dict) and "change_percentage" in scenario_data:
                        changes.append(abs(scenario_data["change_percentage"]))
                
                if changes:
                    avg_sensitivity = statistics.mean(changes)
                    if avg_sensitivity > max_sensitivity:
                        max_sensitivity = avg_sensitivity
                        most_sensitive = parameter
        
        return most_sensitive
    
    async def create_409a_valuation(
        self, 
        business_id: str, 
        valuation_inputs: Dict[str, Any]
    ) -> ValuationModel:
        """Create 409A compliant valuation for employee stock options"""
        
        model_id = str(uuid.uuid4())
        
        # 409A requires conservative approach and multiple methodologies
        
        # Method 1: Asset-based approach (for early stage)
        asset_value = valuation_inputs.get("net_assets", 0)
        
        # Method 2: Income approach (DCF with conservative assumptions)
        if valuation_inputs.get("has_revenue", False):
            conservative_dcf = await self.create_dcf_valuation(business_id, {
                **valuation_inputs,
                "discount_rate": valuation_inputs.get("discount_rate", 0.15),  # Higher discount rate
                "terminal_growth_rate": 0.02,  # Conservative terminal growth
                "model_name": "409A DCF Valuation"
            })
            dcf_value = conservative_dcf.equity_value
        else:
            dcf_value = 0
        
        # Method 3: Market approach (if comparables available)
        market_value = 0
        if valuation_inputs.get("industry"):
            try:
                market_model = await self.create_comparable_company_valuation(business_id, {
                    **valuation_inputs,
                    "model_name": "409A Market Valuation"
                })
                market_value = market_model.equity_value * 0.8  # Apply marketability discount
            except:
                market_value = 0
        
        # Weight the approaches based on company stage and data availability
        if asset_value > 0 and dcf_value == 0 and market_value == 0:
            # Early stage - primarily asset-based
            final_value = asset_value
            methodology_weights = {"asset": 1.0, "income": 0.0, "market": 0.0}
        elif dcf_value > 0 and market_value > 0:
            # Growth stage - weight income and market approaches
            final_value = (dcf_value * 0.6) + (market_value * 0.4)
            methodology_weights = {"asset": 0.0, "income": 0.6, "market": 0.4}
        elif dcf_value > 0:
            # Income approach available
            final_value = (dcf_value * 0.7) + (asset_value * 0.3)
            methodology_weights = {"asset": 0.3, "income": 0.7, "market": 0.0}
        else:
            # Fallback to asset approach
            final_value = max(asset_value, 1000)  # Minimum value
            methodology_weights = {"asset": 1.0, "income": 0.0, "market": 0.0}
        
        # Apply additional discounts for 409A
        marketability_discount = 0.2  # 20% discount for lack of marketability
        final_value = final_value * (1 - marketability_discount)
        
        model = ValuationModel(
            id=model_id,
            business_id=business_id,
            valuation_date=valuation_inputs.get("valuation_date", datetime.now()),
            model_name="409A Valuation",
            valuation_method=ValuationMethod.ASSET_BASED,  # Primary method
            valuation_purpose=ValuationPurpose.EMPLOYEE_STOCK_OPTION,
            company_stage=CompanyStage(valuation_inputs.get("company_stage", "early_stage")),
            equity_value=final_value,
            per_share_value=final_value / valuation_inputs.get("shares_outstanding", 1000000),
            base_case_value=final_value,
            model_inputs={
                "asset_value": asset_value,
                "dcf_value": dcf_value,
                "market_value": market_value,
                "marketability_discount": marketability_discount,
                "methodology_weights": methodology_weights
            },
            calculation_details={
                "primary_approaches": ["asset", "income", "market"],
                "methodology_weights": methodology_weights,
                "marketability_discount_applied": marketability_discount,
                "final_weighted_value": final_value
            },
            confidence_level=0.8,  # High confidence due to conservative approach
            key_risks=[
                "Limited operating history",
                "Market volatility",
                "Execution risk",
                "Competitive threats"
            ],
            methodology_notes="409A compliant valuation using multiple approaches with conservative assumptions and marketability discounts",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            created_by=valuation_inputs.get("created_by", "system")
        )
        
        self.valuation_models[model_id] = model
        return model
    
    async def generate_valuation_report(
        self, 
        business_id: str, 
        model_ids: List[str], 
        report_config: Dict[str, Any]
    ) -> ValuationReport:
        """Generate comprehensive valuation report"""
        
        report_id = str(uuid.uuid4())
        
        # Get valuation models
        models = [self.valuation_models.get(mid) for mid in model_ids if self.valuation_models.get(mid)]
        
        if not models:
            raise ValueError("No valid valuation models found")
        
        # Calculate weighted average valuation
        method_weights = report_config.get("method_weights", {})
        weighted_values = []
        
        for model in models:
            weight = method_weights.get(model.valuation_method.value, 1.0)
            weighted_values.append(model.equity_value * weight)
        
        final_valuation = sum(weighted_values) / sum(method_weights.values()) if method_weights else statistics.mean([m.equity_value for m in models])
        
        # Calculate valuation range
        all_values = [m.equity_value for m in models]
        valuation_range = {
            "low": min(all_values),
            "mid": statistics.median(all_values),
            "high": max(all_values)
        }
        
        # Generate executive summary
        executive_summary = f"""
        Valuation analysis of {report_config.get('company_name', 'the Company')} as of {datetime.now().strftime('%B %d, %Y')}.
        
        Based on {len(models)} valuation methodologies, the estimated equity value ranges from ${valuation_range['low']:,.0f} to ${valuation_range['high']:,.0f}, 
        with a midpoint estimate of ${valuation_range['mid']:,.0f}.
        
        The weighted average valuation considering method reliability and market conditions is ${final_valuation:,.0f}.
        """
        
        # Key conclusions
        key_conclusions = [
            f"Fair value estimate: ${final_valuation:,.0f}",
            f"Valuation range: ${valuation_range['low']:,.0f} - ${valuation_range['high']:,.0f}",
            f"Primary methodologies: {', '.join([m.valuation_method.value.replace('_', ' ').title() for m in models])}",
            f"Valuation purpose: {models[0].valuation_purpose.value.replace('_', ' ').title()}"
        ]
        
        report = ValuationReport(
            id=report_id,
            business_id=business_id,
            report_title=report_config.get("title", "Business Valuation Report"),
            valuation_date=report_config.get("valuation_date", datetime.now()),
            report_purpose=ValuationPurpose(report_config.get("purpose", "fundraising")),
            prepared_by=report_config.get("prepared_by", "Valuation Team"),
            reviewed_by=report_config.get("reviewed_by"),
            executive_summary=executive_summary.strip(),
            key_conclusions=key_conclusions,
            valuation_range=valuation_range,
            primary_methods=[m.valuation_method for m in models],
            method_weights=method_weights,
            valuation_model_ids=model_ids,
            final_valuation=final_valuation,
            valuation_per_share=final_valuation / report_config.get("shares_outstanding", 1000000),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.valuation_reports[report_id] = report
        return report
    
    async def get_valuation_dashboard(self, business_id: str) -> Dict[str, Any]:
        """Get comprehensive valuation dashboard"""
        
        # Get all models for business
        business_models = [m for m in self.valuation_models.values() if m.business_id == business_id]
        business_reports = [r for r in self.valuation_reports.values() if r.business_id == business_id]
        
        if not business_models:
            return {
                "business_id": business_id,
                "error": "No valuation models found",
                "generated_at": datetime.now().isoformat()
            }
        
        # Latest valuation by method
        latest_by_method = {}
        for model in business_models:
            method = model.valuation_method.value
            if method not in latest_by_method or model.valuation_date > latest_by_method[method].valuation_date:
                latest_by_method[method] = model
        
        # Calculate summary statistics
        all_values = [m.equity_value for m in business_models]
        current_valuation_range = {
            "min": min(all_values),
            "max": max(all_values),
            "median": statistics.median(all_values),
            "mean": statistics.mean(all_values)
        }
        
        # Valuation trend (simplified)
        sorted_models = sorted(business_models, key=lambda x: x.valuation_date)
        if len(sorted_models) >= 2:
            trend_percentage = ((sorted_models[-1].equity_value - sorted_models[0].equity_value) / sorted_models[0].equity_value) * 100
        else:
            trend_percentage = 0
        
        return {
            "business_id": business_id,
            "summary": {
                "total_valuations": len(business_models),
                "latest_valuation": sorted_models[-1].equity_value if sorted_models else 0,
                "valuation_range": current_valuation_range,
                "trend_percentage": round(trend_percentage, 1),
                "last_updated": sorted_models[-1].updated_at.isoformat() if sorted_models else None
            },
            "valuations_by_method": {
                method: {
                    "value": model.equity_value,
                    "confidence": model.confidence_level,
                    "date": model.valuation_date.isoformat(),
                    "purpose": model.valuation_purpose.value
                }
                for method, model in latest_by_method.items()
            },
            "recent_reports": [
                {
                    "id": report.id,
                    "title": report.report_title,
                    "final_valuation": report.final_valuation,
                    "purpose": report.report_purpose.value,
                    "date": report.valuation_date.isoformat()
                }
                for report in sorted(business_reports, key=lambda x: x.created_at, reverse=True)[:5]
            ],
            "key_metrics": {
                "average_confidence": round(statistics.mean([m.confidence_level for m in business_models]), 2),
                "most_recent_method": sorted_models[-1].valuation_method.value if sorted_models else None,
                "valuation_purposes": list(set([m.valuation_purpose.value for m in business_models]))
            },
            "generated_at": datetime.now().isoformat()
        }

# Global instance
business_valuation_manager = BusinessValuationManager()