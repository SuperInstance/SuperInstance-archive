"""
Business Controller - Core business management logic
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
import json
import uuid

from ..models.business_types import (
    BusinessEntity, BusinessType, BusinessStatus, FinancialMetrics,
    PerformanceKPI, Investment, RiskAssessment, MarketData,
    create_sample_business, create_sample_financial_metrics,
    calculate_business_score
)

logger = logging.getLogger(__name__)

class BusinessController:
    def __init__(self):
        self.businesses: Dict[str, BusinessEntity] = {}
        self.financial_data: Dict[str, List[FinancialMetrics]] = {}
        self.kpis: Dict[str, List[PerformanceKPI]] = {}
        self.investments: Dict[str, List[Investment]] = {}
        self.risk_assessments: Dict[str, List[RiskAssessment]] = {}
        self.market_data: Dict[str, MarketData] = {}
        
    async def create_business(self, business_data: dict) -> Optional[str]:
        """Create a new business entity"""
        try:
            business_id = business_data.get("business_id") or str(uuid.uuid4())[:8]
            
            business = BusinessEntity(
                business_id=business_id,
                name=business_data["name"],
                type=BusinessType(business_data.get("type", "technology")),
                status=BusinessStatus(business_data.get("status", "planning")),
                industry=business_data.get("industry", "Technology"),
                location=business_data.get("location", "Unknown"),
                founded_date=datetime.fromisoformat(business_data.get("founded_date", datetime.now(timezone.utc).isoformat())),
                description=business_data.get("description", ""),
                website=business_data.get("website"),
                employees_count=business_data.get("employees_count"),
                annual_revenue=Decimal(str(business_data.get("annual_revenue", 0))),
                valuation=Decimal(str(business_data.get("valuation", 0))) if business_data.get("valuation") else None,
                funding_stage=business_data.get("funding_stage"),
                key_executives=business_data.get("key_executives", []),
                business_model=business_data.get("business_model"),
                competitive_advantages=business_data.get("competitive_advantages", []),
                risk_factors=business_data.get("risk_factors", [])
            )
            
            self.businesses[business_id] = business
            
            # Initialize supporting data structures
            self.financial_data[business_id] = []
            self.kpis[business_id] = []
            self.investments[business_id] = []
            self.risk_assessments[business_id] = []
            
            # Create initial financial metrics if revenue provided
            if business.annual_revenue and business.annual_revenue > 0:
                await self._create_initial_financial_metrics(business_id)
            
            logger.info(f"Created business: {business.name} ({business_id})")
            return business_id
            
        except Exception as e:
            logger.error(f"Failed to create business: {e}")
            return None
    
    async def get_business(self, business_id: str) -> Optional[dict]:
        """Get business entity as dictionary"""
        if business_id not in self.businesses:
            return None
        
        business = self.businesses[business_id]
        return {
            "business_id": business.business_id,
            "name": business.name,
            "type": business.type.value,
            "status": business.status.value,
            "industry": business.industry,
            "location": business.location,
            "founded_date": business.founded_date.isoformat(),
            "description": business.description,
            "website": business.website,
            "employees_count": business.employees_count,
            "annual_revenue": float(business.annual_revenue) if business.annual_revenue else None,
            "valuation": float(business.valuation) if business.valuation else None,
            "funding_stage": business.funding_stage,
            "key_executives": business.key_executives,
            "business_model": business.business_model,
            "competitive_advantages": business.competitive_advantages,
            "risk_factors": business.risk_factors,
            "last_updated": business.last_updated.isoformat()
        }
    
    async def get_business_summary(self, business_id: str) -> dict:
        """Get business summary with key metrics"""
        if business_id not in self.businesses:
            return {"error": "Business not found"}
        
        business = self.businesses[business_id]
        
        # Get latest financial metrics
        latest_financials = None
        if business_id in self.financial_data and self.financial_data[business_id]:
            latest_financials = self.financial_data[business_id][-1]
        
        # Calculate business score
        business_score = 0
        if latest_financials:
            business_score = calculate_business_score(business, latest_financials)
        
        # Get key KPIs
        key_kpis = {}
        if business_id in self.kpis:
            for kpi in self.kpis[business_id][-3:]:  # Last 3 KPIs
                key_kpis[kpi.kpi_name] = {
                    "current_value": kpi.current_value,
                    "target_value": kpi.target_value,
                    "unit": kpi.unit,
                    "trend": kpi.trend
                }
        
        # Get investment summary
        investment_summary = {
            "total_investments": len(self.investments.get(business_id, [])),
            "total_amount": sum(
                float(inv.amount) for inv in self.investments.get(business_id, [])
            ),
            "latest_valuation": float(business.valuation) if business.valuation else 0
        }
        
        return {
            "business_id": business_id,
            "name": business.name,
            "type": business.type.value,
            "status": business.status.value,
            "industry": business.industry,
            "business_score": business_score,
            "financial_summary": {
                "annual_revenue": float(business.annual_revenue) if business.annual_revenue else 0,
                "profit": float(latest_financials.profit) if latest_financials else 0,
                "profit_margin": latest_financials.profit_margin if latest_financials else 0,
                "cash_flow": float(latest_financials.cash_flow) if latest_financials else 0
            } if latest_financials else None,
            "key_kpis": key_kpis,
            "investment_summary": investment_summary,
            "employee_count": business.employees_count,
            "last_updated": business.last_updated.isoformat()
        }
    
    async def get_business_details(self, business_id: str) -> dict:
        """Get comprehensive business details"""
        if business_id not in self.businesses:
            return {"error": "Business not found"}
        
        business_dict = await self.get_business(business_id)
        
        # Add detailed financial history
        financial_history = []
        if business_id in self.financial_data:
            for metrics in self.financial_data[business_id]:
                financial_history.append({
                    "period_start": metrics.period_start.isoformat(),
                    "period_end": metrics.period_end.isoformat(),
                    "revenue": float(metrics.revenue),
                    "profit": float(metrics.profit),
                    "profit_margin": metrics.profit_margin,
                    "cash_flow": float(metrics.cash_flow),
                    "return_on_investment": metrics.return_on_investment
                })
        
        # Add KPI details
        kpi_details = []
        if business_id in self.kpis:
            for kpi in self.kpis[business_id]:
                kpi_details.append({
                    "kpi_name": kpi.kpi_name,
                    "current_value": kpi.current_value,
                    "target_value": kpi.target_value,
                    "unit": kpi.unit,
                    "category": kpi.category,
                    "trend": kpi.trend,
                    "last_updated": kpi.last_updated.isoformat()
                })
        
        # Add investment details
        investment_details = []
        if business_id in self.investments:
            for investment in self.investments[business_id]:
                investment_details.append({
                    "investment_id": investment.investment_id,
                    "investor_id": investment.investor_id,
                    "type": investment.type.value,
                    "amount": float(investment.amount),
                    "equity_percentage": investment.equity_percentage,
                    "investment_date": investment.investment_date.isoformat(),
                    "status": investment.status,
                    "expected_return": investment.expected_return
                })
        
        # Add risk assessment
        risk_details = []
        if business_id in self.risk_assessments:
            for risk in self.risk_assessments[business_id]:
                risk_details.append({
                    "risk_category": risk.risk_category,
                    "risk_description": risk.risk_description,
                    "likelihood": risk.likelihood,
                    "impact_severity": risk.impact_severity,
                    "risk_score": risk.risk_score,
                    "mitigation_strategies": risk.mitigation_strategies,
                    "status": risk.status
                })
        
        business_dict.update({
            "financial_history": financial_history,
            "kpi_details": kpi_details,
            "investment_details": investment_details,
            "risk_assessments": risk_details,
            "market_data": self.market_data.get(business.industry, {})
        })
        
        return business_dict
    
    async def update_business(self, business_id: str, updates: dict) -> bool:
        """Update business entity"""
        if business_id not in self.businesses:
            return False
        
        try:
            business = self.businesses[business_id]
            
            # Update allowed fields
            if "name" in updates:
                business.name = updates["name"]
            if "status" in updates:
                business.status = BusinessStatus(updates["status"])
            if "description" in updates:
                business.description = updates["description"]
            if "website" in updates:
                business.website = updates["website"]
            if "employees_count" in updates:
                business.employees_count = updates["employees_count"]
            if "annual_revenue" in updates:
                business.annual_revenue = Decimal(str(updates["annual_revenue"]))
            if "valuation" in updates:
                business.valuation = Decimal(str(updates["valuation"]))
            if "funding_stage" in updates:
                business.funding_stage = updates["funding_stage"]
            if "key_executives" in updates:
                business.key_executives = updates["key_executives"]
            if "business_model" in updates:
                business.business_model = updates["business_model"]
            if "competitive_advantages" in updates:
                business.competitive_advantages = updates["competitive_advantages"]
            if "risk_factors" in updates:
                business.risk_factors = updates["risk_factors"]
            
            business.last_updated = datetime.now(timezone.utc)
            
            logger.info(f"Updated business: {business.name} ({business_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update business {business_id}: {e}")
            return False
    
    async def update_financial_data(self, business_id: str, financial_data: dict) -> bool:
        """Update financial data for business"""
        if business_id not in self.businesses:
            return False
        
        try:
            metrics = FinancialMetrics(
                revenue=Decimal(str(financial_data["revenue"])),
                expenses=Decimal(str(financial_data["expenses"])),
                profit=Decimal(str(financial_data["profit"])),
                profit_margin=financial_data["profit_margin"],
                cash_flow=Decimal(str(financial_data["cash_flow"])),
                assets=Decimal(str(financial_data["assets"])),
                liabilities=Decimal(str(financial_data["liabilities"])),
                equity=Decimal(str(financial_data["equity"])),
                debt_to_equity_ratio=financial_data["debt_to_equity_ratio"],
                return_on_investment=financial_data["return_on_investment"],
                period_start=datetime.fromisoformat(financial_data["period_start"]),
                period_end=datetime.fromisoformat(financial_data["period_end"]),
                currency=financial_data.get("currency", "USD")
            )
            
            if business_id not in self.financial_data:
                self.financial_data[business_id] = []
            
            self.financial_data[business_id].append(metrics)
            
            # Keep only last 24 months of data
            self.financial_data[business_id] = self.financial_data[business_id][-24:]
            
            logger.info(f"Updated financial data for business {business_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update financial data for {business_id}: {e}")
            return False
    
    async def update_performance_metrics(self, business_id: str) -> bool:
        """Update performance metrics and KPIs"""
        if business_id not in self.businesses:
            return False
        
        try:
            # Simulate performance metric updates
            business = self.businesses[business_id]
            current_time = datetime.now(timezone.utc)
            
            # Update existing KPIs or create new ones
            if business_id not in self.kpis:
                self.kpis[business_id] = []
            
            # Revenue-based KPIs
            if business.annual_revenue:
                monthly_revenue = float(business.annual_revenue) / 12
                revenue_kpi = PerformanceKPI(
                    kpi_id=f"mrr_{current_time.strftime('%Y%m')}",
                    business_id=business_id,
                    kpi_name="Monthly Recurring Revenue",
                    current_value=monthly_revenue,
                    target_value=monthly_revenue * 1.15,  # 15% growth target
                    unit="USD",
                    category="financial",
                    frequency="monthly",
                    trend="stable",
                    last_updated=current_time
                )
                self.kpis[business_id].append(revenue_kpi)
            
            # Employee productivity KPI
            if business.employees_count:
                revenue_per_employee = float(business.annual_revenue or 0) / business.employees_count
                productivity_kpi = PerformanceKPI(
                    kpi_id=f"rpe_{current_time.strftime('%Y%m')}",
                    business_id=business_id,
                    kpi_name="Revenue per Employee",
                    current_value=revenue_per_employee,
                    target_value=revenue_per_employee * 1.1,
                    unit="USD",
                    category="operational",
                    frequency="monthly",
                    trend="improving" if revenue_per_employee > 100000 else "stable",
                    last_updated=current_time
                )
                self.kpis[business_id].append(productivity_kpi)
            
            # Keep only recent KPIs
            self.kpis[business_id] = self.kpis[business_id][-50:]
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update performance metrics for {business_id}: {e}")
            return False
    
    async def _create_initial_financial_metrics(self, business_id: str):
        """Create initial financial metrics for new business"""
        business = self.businesses[business_id]
        
        # Create basic financial metrics based on annual revenue
        annual_revenue = business.annual_revenue
        estimated_expenses = annual_revenue * Decimal("0.7")  # 70% expense ratio
        profit = annual_revenue - estimated_expenses
        
        current_year = datetime.now(timezone.utc).year
        
        metrics = FinancialMetrics(
            revenue=annual_revenue,
            expenses=estimated_expenses,
            profit=profit,
            profit_margin=float(profit / annual_revenue) if annual_revenue > 0 else 0,
            cash_flow=profit * Decimal("1.1"),  # Slight positive cash flow adjustment
            assets=annual_revenue * Decimal("1.5"),  # Estimated assets
            liabilities=annual_revenue * Decimal("0.3"),  # Estimated liabilities
            equity=annual_revenue * Decimal("1.2"),  # Estimated equity
            debt_to_equity_ratio=0.25,  # Conservative debt ratio
            return_on_investment=0.2,  # Estimated ROI
            period_start=datetime(current_year, 1, 1, tzinfo=timezone.utc),
            period_end=datetime(current_year, 12, 31, tzinfo=timezone.utc)
        )
        
        self.financial_data[business_id] = [metrics]
        
        logger.info(f"Created initial financial metrics for {business.name}")
    
    async def get_status(self) -> bool:
        """Get controller operational status"""
        return len(self.businesses) >= 0  # Always operational if businesses dict exists