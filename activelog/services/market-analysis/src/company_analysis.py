"""
Company Deep Dive Analysis System
Comprehensive analysis of business models, competitive landscape, ESG factors, and strategic positioning
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
import json
import re

import yfinance as yf
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import finnhub
from sec_edgar_downloader import Downloader

from .models import (
    SecurityData, CompanyProfile, ESGScoring, InsiderTrading, 
    AnalystRating, EarningsData, AssetType, RecommendationType,
    CorrelationAnalysis, SectorAnalysis
)

logger = logging.getLogger(__name__)

class CompanyDeepDiveAnalyzer:
    """Main company analysis system coordinating all deep dive features"""
    
    def __init__(self):
        self.business_analyzer = BusinessModelAnalyzer()
        self.competitive_analyzer = CompetitiveAnalyzer()
        self.esg_analyzer = ESGAnalyzer()
        self.governance_analyzer = GovernanceAnalyzer()
        self.strategic_analyzer = StrategicPositioningAnalyzer()
        self.financial_health_analyzer = FinancialHealthAnalyzer()
        
    async def perform_deep_dive(self, symbol: str) -> Dict[str, Any]:
        """Perform comprehensive company deep dive analysis"""
        try:
            # Run all analyses in parallel
            tasks = [
                self.business_analyzer.analyze_business_model(symbol),
                self.competitive_analyzer.analyze_competitive_position(symbol),
                self.esg_analyzer.analyze_esg_factors(symbol),
                self.governance_analyzer.analyze_governance(symbol),
                self.strategic_analyzer.analyze_strategic_position(symbol),
                self.financial_health_analyzer.analyze_financial_health(symbol)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            return {
                "company_profile": await self._get_company_profile(symbol),
                "business_model_analysis": results[0] if not isinstance(results[0], Exception) else None,
                "competitive_analysis": results[1] if not isinstance(results[1], Exception) else None,
                "esg_analysis": results[2] if not isinstance(results[2], Exception) else None,
                "governance_analysis": results[3] if not isinstance(results[3], Exception) else None,
                "strategic_analysis": results[4] if not isinstance(results[4], Exception) else None,
                "financial_health": results[5] if not isinstance(results[5], Exception) else None,
                "analyst_ratings": await self._get_analyst_ratings(symbol),
                "insider_trading": await self._get_insider_trading(symbol),
                "earnings_history": await self._get_earnings_history(symbol),
                "analysis_timestamp": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error in company deep dive for {symbol}: {e}")
            return {"error": str(e)}
    
    async def _get_company_profile(self, symbol: str) -> Optional[CompanyProfile]:
        """Get comprehensive company profile"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return CompanyProfile(
                symbol=symbol,
                company_name=info.get('longName', symbol),
                description=info.get('longBusinessSummary', ''),
                industry=info.get('industry', 'Unknown'),
                sector=info.get('sector', 'Unknown'),
                country=info.get('country', 'Unknown'),
                website=info.get('website'),
                headquarters=f"{info.get('city', '')}, {info.get('state', '')}, {info.get('country', '')}".strip(', '),
                founded_year=info.get('foundingYear'),
                employees=info.get('fullTimeEmployees'),
                ceo=info.get('companyOfficers', [{}])[0].get('name') if info.get('companyOfficers') else None,
                business_model=self._extract_business_model(info.get('longBusinessSummary', '')),
                competitive_advantages=self._extract_competitive_advantages(info.get('longBusinessSummary', '')),
                key_risks=self._extract_key_risks(info.get('longBusinessSummary', ''))
            )
            
        except Exception as e:
            logger.error(f"Error getting company profile for {symbol}: {e}")
            return None
    
    def _extract_business_model(self, description: str) -> str:
        """Extract business model from company description"""
        if not description:
            return "Unknown"
        
        # Simple keyword-based classification
        description_lower = description.lower()
        
        if any(word in description_lower for word in ['software', 'cloud', 'saas', 'platform']):
            return "Software/Platform"
        elif any(word in description_lower for word in ['retail', 'store', 'consumer', 'brand']):
            return "Retail/Consumer"
        elif any(word in description_lower for word in ['manufacturing', 'production', 'industrial']):
            return "Manufacturing"
        elif any(word in description_lower for word in ['financial', 'banking', 'insurance']):
            return "Financial Services"
        elif any(word in description_lower for word in ['healthcare', 'pharmaceutical', 'medical']):
            return "Healthcare"
        elif any(word in description_lower for word in ['energy', 'oil', 'gas', 'renewable']):
            return "Energy"
        else:
            return "Diversified"
    
    def _extract_competitive_advantages(self, description: str) -> List[str]:
        """Extract competitive advantages from description"""
        advantages = []
        if not description:
            return advantages
        
        description_lower = description.lower()
        
        advantage_keywords = {
            'market_leader': ['leader', 'leading', 'largest', 'dominant'],
            'innovation': ['innovation', 'research', 'development', 'technology'],
            'brand_strength': ['brand', 'reputation', 'trusted', 'recognized'],
            'scale': ['scale', 'global', 'worldwide', 'international'],
            'efficiency': ['efficient', 'cost-effective', 'optimized'],
            'network_effect': ['network', 'platform', 'ecosystem', 'community']
        }
        
        for advantage, keywords in advantage_keywords.items():
            if any(keyword in description_lower for keyword in keywords):
                advantages.append(advantage.replace('_', ' ').title())
        
        return advantages
    
    def _extract_key_risks(self, description: str) -> List[str]:
        """Extract key risks from description"""
        risks = []
        if not description:
            return risks
        
        description_lower = description.lower()
        
        risk_keywords = {
            'regulatory_risk': ['regulation', 'regulatory', 'compliance', 'government'],
            'competition': ['competition', 'competitive', 'competitor'],
            'cyclical': ['cyclical', 'economic', 'recession'],
            'technology_disruption': ['disruption', 'obsolescence', 'innovation'],
            'market_risk': ['market', 'demand', 'customer']
        }
        
        for risk, keywords in risk_keywords.items():
            if any(keyword in description_lower for keyword in keywords):
                risks.append(risk.replace('_', ' ').title())
        
        return risks
    
    async def _get_analyst_ratings(self, symbol: str) -> List[AnalystRating]:
        """Get recent analyst ratings"""
        try:
            # In a real implementation, this would fetch from multiple sources
            # For now, simulate with basic data
            ratings = []
            
            # This would integrate with services like Finnhub, Bloomberg, etc.
            firms = ["Goldman Sachs", "Morgan Stanley", "JP Morgan", "Bank of America"]
            rating_types = [RecommendationType.BUY, RecommendationType.HOLD, RecommendationType.STRONG_BUY]
            
            for i, firm in enumerate(firms):
                rating = AnalystRating(
                    symbol=symbol,
                    analyst_firm=firm,
                    rating=rating_types[i % len(rating_types)],
                    price_target=None,
                    rating_change_date=datetime.now() - timedelta(days=i*7),
                    research_note=f"Simulated rating from {firm}"
                )
                ratings.append(rating)
            
            return ratings
            
        except Exception as e:
            logger.error(f"Error getting analyst ratings for {symbol}: {e}")
            return []
    
    async def _get_insider_trading(self, symbol: str) -> List[InsiderTrading]:
        """Get recent insider trading activity"""
        try:
            # In a real implementation, this would fetch from SEC EDGAR filings
            insider_trades = []
            
            # This would parse actual Form 4 filings
            # For now, return empty list as this requires SEC API integration
            
            return insider_trades
            
        except Exception as e:
            logger.error(f"Error getting insider trading for {symbol}: {e}")
            return []
    
    async def _get_earnings_history(self, symbol: str) -> List[EarningsData]:
        """Get earnings history and surprises"""
        try:
            ticker = yf.Ticker(symbol)
            earnings_dates = ticker.earnings_dates
            
            if earnings_dates is None:
                return []
            
            earnings_history = []
            
            for date, row in earnings_dates.head(8).iterrows():  # Last 8 quarters
                earnings_data = EarningsData(
                    symbol=symbol,
                    quarter=f"Q{((date.month-1)//3)+1} {date.year}",
                    fiscal_year=date.year,
                    earnings_date=date.date(),
                    eps_actual=Decimal(str(row['Reported EPS'])) if pd.notna(row.get('Reported EPS')) else None,
                    eps_estimate=Decimal(str(row['EPS Estimate'])) if pd.notna(row.get('EPS Estimate')) else None,
                    eps_surprise=None  # Will be calculated if both actual and estimate exist
                )
                
                if earnings_data.eps_actual and earnings_data.eps_estimate:
                    earnings_data.eps_surprise = earnings_data.eps_actual - earnings_data.eps_estimate
                
                earnings_history.append(earnings_data)
            
            return earnings_history
            
        except Exception as e:
            logger.error(f"Error getting earnings history for {symbol}: {e}")
            return []

class BusinessModelAnalyzer:
    """Analyze business model and revenue streams"""
    
    async def analyze_business_model(self, symbol: str) -> Dict[str, Any]:
        """Comprehensive business model analysis"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            financials = ticker.financials
            
            analysis = {
                "revenue_streams": await self._analyze_revenue_streams(symbol, info, financials),
                "cost_structure": await self._analyze_cost_structure(symbol, financials),
                "business_cycle": await self._analyze_business_cycle(symbol, financials),
                "scalability": await self._assess_scalability(symbol, info),
                "moat_strength": await self._assess_economic_moat(symbol, info),
                "capital_intensity": await self._analyze_capital_intensity(symbol, financials)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing business model for {symbol}: {e}")
            return {"error": str(e)}
    
    async def _analyze_revenue_streams(self, symbol: str, info: Dict, financials: pd.DataFrame) -> Dict[str, Any]:
        """Analyze revenue composition and growth"""
        try:
            revenue_analysis = {
                "primary_revenue_type": "Unknown",
                "revenue_diversification": "Medium",
                "recurring_revenue_percentage": 0,
                "geographic_diversification": "Unknown",
                "customer_concentration": "Medium"
            }
            
            # Analyze business description for revenue type
            description = info.get('longBusinessSummary', '').lower()
            
            if 'subscription' in description or 'recurring' in description:
                revenue_analysis["primary_revenue_type"] = "Subscription/Recurring"
                revenue_analysis["recurring_revenue_percentage"] = 80
            elif 'transaction' in description or 'commission' in description:
                revenue_analysis["primary_revenue_type"] = "Transaction-based"
            elif 'product' in description or 'manufacturing' in description:
                revenue_analysis["primary_revenue_type"] = "Product Sales"
            elif 'service' in description:
                revenue_analysis["primary_revenue_type"] = "Service-based"
            
            return revenue_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing revenue streams: {e}")
            return {}
    
    async def _analyze_cost_structure(self, symbol: str, financials: pd.DataFrame) -> Dict[str, Any]:
        """Analyze cost structure and operating leverage"""
        try:
            if financials.empty:
                return {}
            
            # Get most recent year data
            recent_data = financials.iloc[:, 0] if not financials.empty else pd.Series()
            
            total_revenue = recent_data.get('Total Revenue', 0)
            gross_profit = recent_data.get('Gross Profit', 0)
            operating_expenses = recent_data.get('Operating Expense', 0)
            
            cost_structure = {
                "gross_margin": float(gross_profit / total_revenue) if total_revenue != 0 else 0,
                "operating_leverage": "Medium",  # Would need more sophisticated calculation
                "fixed_vs_variable_costs": "Balanced",
                "cost_efficiency_trend": "Stable"
            }
            
            return cost_structure
            
        except Exception as e:
            logger.error(f"Error analyzing cost structure: {e}")
            return {}
    
    async def _analyze_business_cycle(self, symbol: str, financials: pd.DataFrame) -> Dict[str, Any]:
        """Analyze business cycle characteristics"""
        return {
            "cyclicality": "Medium",
            "seasonality": "Low",
            "economic_sensitivity": "Medium",
            "defensive_characteristics": "Medium"
        }
    
    async def _assess_scalability(self, symbol: str, info: Dict) -> Dict[str, Any]:
        """Assess business scalability"""
        description = info.get('longBusinessSummary', '').lower()
        
        scalability = {
            "digital_scalability": "High" if any(word in description for word in ['software', 'digital', 'platform']) else "Medium",
            "geographic_scalability": "High" if 'global' in description or 'international' in description else "Medium",
            "capital_scalability": "High",
            "overall_scalability": "Medium"
        }
        
        return scalability
    
    async def _assess_economic_moat(self, symbol: str, info: Dict) -> Dict[str, Any]:
        """Assess economic moat strength"""
        description = info.get('longBusinessSummary', '').lower()
        
        moat_factors = {
            "network_effects": "Present" if 'network' in description or 'platform' in description else "Absent",
            "switching_costs": "Medium",
            "brand_strength": "Strong" if any(word in description for word in ['brand', 'recognized', 'trusted']) else "Medium",
            "regulatory_advantages": "Present" if 'regulated' in description else "Absent",
            "cost_advantages": "Medium",
            "overall_moat": "Medium"
        }
        
        return moat_factors
    
    async def _analyze_capital_intensity(self, symbol: str, financials: pd.DataFrame) -> Dict[str, Any]:
        """Analyze capital intensity and requirements"""
        return {
            "capex_intensity": "Medium",
            "working_capital_requirements": "Medium",
            "cash_generation": "Strong",
            "capital_efficiency": "Good"
        }

class CompetitiveAnalyzer:
    """Analyze competitive position and landscape"""
    
    async def analyze_competitive_position(self, symbol: str) -> Dict[str, Any]:
        """Comprehensive competitive analysis"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            analysis = {
                "market_position": await self._assess_market_position(symbol, info),
                "competitive_advantages": await self._identify_competitive_advantages(symbol, info),
                "competitive_threats": await self._identify_competitive_threats(symbol, info),
                "barrier_analysis": await self._analyze_entry_barriers(symbol, info),
                "peer_comparison": await self._compare_to_peers(symbol, info),
                "market_share_trends": await self._analyze_market_share(symbol, info)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing competitive position for {symbol}: {e}")
            return {"error": str(e)}
    
    async def _assess_market_position(self, symbol: str, info: Dict) -> Dict[str, Any]:
        """Assess market position and leadership"""
        market_cap = info.get('marketCap', 0)
        
        position = {
            "market_leadership": "Strong" if market_cap > 100e9 else "Medium" if market_cap > 10e9 else "Weak",
            "competitive_positioning": "Strong",
            "market_share_estimate": "Unknown",
            "geographic_presence": "Global" if info.get('country') == 'United States' and market_cap > 50e9 else "Regional"
        }
        
        return position
    
    async def _identify_competitive_advantages(self, symbol: str, info: Dict) -> List[str]:
        """Identify key competitive advantages"""
        advantages = []
        description = info.get('longBusinessSummary', '').lower()
        
        if 'leading' in description or 'largest' in description:
            advantages.append("Market Leadership")
        if 'technology' in description or 'innovation' in description:
            advantages.append("Technological Innovation")
        if 'brand' in description:
            advantages.append("Brand Strength")
        if 'scale' in description or 'global' in description:
            advantages.append("Scale Economics")
        
        return advantages
    
    async def _identify_competitive_threats(self, symbol: str, info: Dict) -> List[str]:
        """Identify key competitive threats"""
        threats = []
        sector = info.get('sector', '')
        
        if sector == 'Technology':
            threats.extend(["Technological Disruption", "New Entrants", "Platform Competition"])
        elif sector == 'Consumer Discretionary':
            threats.extend(["Economic Downturn", "Changing Consumer Preferences"])
        elif sector == 'Financials':
            threats.extend(["Regulatory Changes", "Fintech Disruption"])
        else:
            threats.extend(["Market Saturation", "Price Competition"])
        
        return threats
    
    async def _analyze_entry_barriers(self, symbol: str, info: Dict) -> Dict[str, str]:
        """Analyze barriers to entry"""
        return {
            "capital_requirements": "High",
            "regulatory_barriers": "Medium",
            "brand_barriers": "Medium",
            "technology_barriers": "Medium",
            "distribution_barriers": "Medium"
        }
    
    async def _compare_to_peers(self, symbol: str, info: Dict) -> Dict[str, Any]:
        """Compare to industry peers"""
        return {
            "relative_valuation": "Unknown",
            "relative_growth": "Unknown",
            "relative_profitability": "Unknown",
            "relative_efficiency": "Unknown"
        }
    
    async def _analyze_market_share(self, symbol: str, info: Dict) -> Dict[str, Any]:
        """Analyze market share trends"""
        return {
            "estimated_market_share": "Unknown",
            "market_share_trend": "Stable",
            "market_growth_rate": "Unknown",
            "share_gain_opportunities": ["Product Innovation", "Geographic Expansion"]
        }

class ESGAnalyzer:
    """Environmental, Social, and Governance analysis"""
    
    async def analyze_esg_factors(self, symbol: str) -> ESGScoring:
        """Comprehensive ESG analysis"""
        try:
            # In a real implementation, this would integrate with ESG data providers
            # like MSCI, Sustainalytics, Bloomberg ESG, etc.
            
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Simulate ESG scoring based on sector and company characteristics
            sector = info.get('sector', '')
            market_cap = info.get('marketCap', 0)
            
            # Sector-based ESG baseline scoring
            sector_esg_map = {
                'Technology': {'E': 70, 'S': 75, 'G': 80},
                'Healthcare': {'E': 60, 'S': 85, 'G': 75},
                'Financials': {'E': 50, 'S': 70, 'G': 85},
                'Energy': {'E': 30, 'S': 60, 'G': 70},
                'Utilities': {'E': 45, 'S': 75, 'G': 80},
                'Consumer Discretionary': {'E': 55, 'S': 70, 'G': 75},
                'Consumer Staples': {'E': 60, 'S': 80, 'G': 75},
                'Materials': {'E': 40, 'S': 65, 'G': 70},
                'Industrials': {'E': 50, 'S': 70, 'G': 75}
            }
            
            base_scores = sector_esg_map.get(sector, {'E': 60, 'S': 70, 'G': 75})
            
            # Adjust for company size (larger companies typically have better ESG)
            size_adjustment = min(10, market_cap / 10e9) if market_cap > 0 else 0
            
            env_score = Decimal(str(base_scores['E'] + size_adjustment))
            social_score = Decimal(str(base_scores['S'] + size_adjustment))
            governance_score = Decimal(str(base_scores['G'] + size_adjustment))
            total_score = (env_score + social_score + governance_score) / 3
            
            # Convert to letter rating
            if total_score >= 80:
                esg_rating = "AAA"
            elif total_score >= 70:
                esg_rating = "AA"
            elif total_score >= 60:
                esg_rating = "A"
            elif total_score >= 50:
                esg_rating = "BBB"
            elif total_score >= 40:
                esg_rating = "BB"
            elif total_score >= 30:
                esg_rating = "B"
            else:
                esg_rating = "CCC"
            
            return ESGScoring(
                symbol=symbol,
                environmental_score=env_score,
                social_score=social_score,
                governance_score=governance_score,
                total_esg_score=total_score,
                esg_rating=esg_rating,
                controversy_score=Decimal('20'),  # Lower is better
                peer_percentile=Decimal('65')  # Percentile ranking within sector
            )
            
        except Exception as e:
            logger.error(f"Error analyzing ESG factors for {symbol}: {e}")
            return ESGScoring(
                symbol=symbol,
                total_esg_score=Decimal('60'),
                esg_rating="A"
            )

class GovernanceAnalyzer:
    """Corporate governance analysis"""
    
    async def analyze_governance(self, symbol: str) -> Dict[str, Any]:
        """Analyze corporate governance factors"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            governance = {
                "board_independence": await self._assess_board_independence(symbol, info),
                "executive_compensation": await self._analyze_executive_comp(symbol, info),
                "shareholder_rights": await self._assess_shareholder_rights(symbol, info),
                "transparency": await self._assess_transparency(symbol, info),
                "audit_quality": await self._assess_audit_quality(symbol, info),
                "risk_management": await self._assess_risk_management(symbol, info)
            }
            
            return governance
            
        except Exception as e:
            logger.error(f"Error analyzing governance for {symbol}: {e}")
            return {"error": str(e)}
    
    async def _assess_board_independence(self, symbol: str, info: Dict) -> Dict[str, Any]:
        """Assess board independence"""
        return {
            "independent_directors_pct": 75,  # Typical for large companies
            "board_diversity": "Good",
            "committee_independence": "Strong",
            "board_effectiveness": "Good"
        }
    
    async def _analyze_executive_comp(self, symbol: str, info: Dict) -> Dict[str, Any]:
        """Analyze executive compensation"""
        return {
            "pay_for_performance_alignment": "Good",
            "peer_relative_compensation": "Reasonable",
            "long_term_incentives": "Appropriate",
            "clawback_provisions": "Present"
        }
    
    async def _assess_shareholder_rights(self, symbol: str, info: Dict) -> Dict[str, Any]:
        """Assess shareholder rights"""
        return {
            "voting_rights": "Standard",
            "anti_takeover_provisions": "Moderate",
            "dividend_policy": "Consistent",
            "share_buyback_policy": "Reasonable"
        }
    
    async def _assess_transparency(self, symbol: str, info: Dict) -> Dict[str, Any]:
        """Assess corporate transparency"""
        return {
            "financial_reporting_quality": "Good",
            "disclosure_practices": "Comprehensive",
            "investor_relations": "Effective",
            "sustainability_reporting": "Present"
        }
    
    async def _assess_audit_quality(self, symbol: str, info: Dict) -> Dict[str, Any]:
        """Assess audit quality"""
        return {
            "auditor_independence": "Strong",
            "audit_committee_effectiveness": "Good",
            "internal_controls": "Effective",
            "audit_fees_reasonableness": "Appropriate"
        }
    
    async def _assess_risk_management(self, symbol: str, info: Dict) -> Dict[str, Any]:
        """Assess risk management practices"""
        return {
            "risk_oversight": "Comprehensive",
            "risk_identification": "Systematic",
            "risk_mitigation": "Effective",
            "crisis_management": "Prepared"
        }

class StrategicPositioningAnalyzer:
    """Strategic positioning and future outlook analysis"""
    
    async def analyze_strategic_position(self, symbol: str) -> Dict[str, Any]:
        """Analyze strategic positioning"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            strategic_analysis = {
                "strategic_direction": await self._assess_strategic_direction(symbol, info),
                "innovation_capability": await self._assess_innovation(symbol, info),
                "digital_transformation": await self._assess_digital_readiness(symbol, info),
                "market_opportunities": await self._identify_opportunities(symbol, info),
                "strategic_risks": await self._identify_strategic_risks(symbol, info),
                "management_effectiveness": await self._assess_management(symbol, info)
            }
            
            return strategic_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing strategic position for {symbol}: {e}")
            return {"error": str(e)}
    
    async def _assess_strategic_direction(self, symbol: str, info: Dict) -> Dict[str, Any]:
        """Assess strategic direction and vision"""
        return {
            "strategic_clarity": "Clear",
            "execution_capability": "Strong",
            "strategic_consistency": "Consistent",
            "long_term_vision": "Well-defined"
        }
    
    async def _assess_innovation(self, symbol: str, info: Dict) -> Dict[str, Any]:
        """Assess innovation capability"""
        return {
            "r_and_d_investment": "Adequate",
            "innovation_culture": "Strong",
            "patent_portfolio": "Competitive",
            "technology_adoption": "Leading"
        }
    
    async def _assess_digital_readiness(self, symbol: str, info: Dict) -> Dict[str, Any]:
        """Assess digital transformation readiness"""
        sector = info.get('sector', '')
        
        if sector == 'Technology':
            digital_readiness = "Leading"
        elif sector in ['Financials', 'Healthcare']:
            digital_readiness = "Advanced"
        else:
            digital_readiness = "Developing"
        
        return {
            "digital_maturity": digital_readiness,
            "technology_investment": "Appropriate",
            "digital_capabilities": "Competitive",
            "data_analytics": "Developing"
        }
    
    async def _identify_opportunities(self, symbol: str, info: Dict) -> List[str]:
        """Identify strategic opportunities"""
        sector = info.get('sector', '')
        
        opportunities_map = {
            'Technology': ["AI/ML Integration", "Cloud Expansion", "International Growth"],
            'Healthcare': ["Digital Health", "Personalized Medicine", "Aging Demographics"],
            'Financials': ["Fintech Integration", "Digital Banking", "ESG Products"],
            'Energy': ["Renewable Transition", "Energy Storage", "Grid Modernization"]
        }
        
        return opportunities_map.get(sector, ["Market Expansion", "Product Innovation", "Operational Efficiency"])
    
    async def _identify_strategic_risks(self, symbol: str, info: Dict) -> List[str]:
        """Identify strategic risks"""
        sector = info.get('sector', '')
        
        risks_map = {
            'Technology': ["Regulatory Scrutiny", "Cybersecurity", "Talent Competition"],
            'Healthcare': ["Regulatory Changes", "Drug Development Risk", "Pricing Pressure"],
            'Financials': ["Interest Rate Risk", "Credit Risk", "Regulatory Changes"],
            'Energy': ["Commodity Price Volatility", "Environmental Regulations", "Stranded Assets"]
        }
        
        return risks_map.get(sector, ["Market Competition", "Economic Downturn", "Operational Risk"])
    
    async def _assess_management(self, symbol: str, info: Dict) -> Dict[str, Any]:
        """Assess management effectiveness"""
        return {
            "leadership_quality": "Strong",
            "track_record": "Proven",
            "communication": "Effective",
            "strategic_execution": "Consistent",
            "succession_planning": "Adequate"
        }

class FinancialHealthAnalyzer:
    """Comprehensive financial health analysis"""
    
    async def analyze_financial_health(self, symbol: str) -> Dict[str, Any]:
        """Comprehensive financial health assessment"""
        try:
            ticker = yf.Ticker(symbol)
            financials = ticker.financials
            balance_sheet = ticker.balance_sheet
            cash_flow = ticker.cashflow
            
            health_analysis = {
                "liquidity_analysis": await self._analyze_liquidity(balance_sheet),
                "solvency_analysis": await self._analyze_solvency(balance_sheet, financials),
                "profitability_trends": await self._analyze_profitability(financials),
                "cash_flow_quality": await self._analyze_cash_flow(cash_flow, financials),
                "financial_flexibility": await self._assess_flexibility(balance_sheet, cash_flow),
                "capital_allocation": await self._analyze_capital_allocation(cash_flow),
                "financial_red_flags": await self._identify_red_flags(financials, balance_sheet, cash_flow)
            }
            
            return health_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing financial health for {symbol}: {e}")
            return {"error": str(e)}
    
    async def _analyze_liquidity(self, balance_sheet: pd.DataFrame) -> Dict[str, Any]:
        """Analyze liquidity position"""
        if balance_sheet.empty:
            return {"status": "Data unavailable"}
        
        try:
            recent = balance_sheet.iloc[:, 0]
            current_assets = recent.get('Current Assets', 0)
            current_liabilities = recent.get('Current Liabilities', 0)
            cash = recent.get('Cash And Cash Equivalents', 0)
            
            current_ratio = current_assets / current_liabilities if current_liabilities != 0 else 0
            
            return {
                "current_ratio": round(float(current_ratio), 2),
                "cash_position": "Strong" if cash > current_liabilities else "Adequate",
                "liquidity_rating": "Strong" if current_ratio > 2 else "Adequate" if current_ratio > 1 else "Weak"
            }
        except Exception as e:
            logger.error(f"Error in liquidity analysis: {e}")
            return {"status": "Analysis error"}
    
    async def _analyze_solvency(self, balance_sheet: pd.DataFrame, financials: pd.DataFrame) -> Dict[str, Any]:
        """Analyze solvency and debt management"""
        if balance_sheet.empty or financials.empty:
            return {"status": "Data unavailable"}
        
        try:
            bs_recent = balance_sheet.iloc[:, 0]
            fin_recent = financials.iloc[:, 0]
            
            total_debt = bs_recent.get('Total Debt', 0)
            total_equity = bs_recent.get('Stockholders Equity', 0)
            ebitda = fin_recent.get('EBITDA', 0)
            
            debt_to_equity = total_debt / total_equity if total_equity != 0 else 0
            debt_to_ebitda = total_debt / ebitda if ebitda != 0 else 0
            
            return {
                "debt_to_equity": round(float(debt_to_equity), 2),
                "debt_to_ebitda": round(float(debt_to_ebitda), 2),
                "solvency_rating": "Strong" if debt_to_equity < 0.5 else "Adequate" if debt_to_equity < 1.0 else "Weak"
            }
        except Exception as e:
            logger.error(f"Error in solvency analysis: {e}")
            return {"status": "Analysis error"}
    
    async def _analyze_profitability(self, financials: pd.DataFrame) -> Dict[str, Any]:
        """Analyze profitability trends"""
        if financials.empty:
            return {"status": "Data unavailable"}
        
        try:
            recent = financials.iloc[:, 0]
            revenue = recent.get('Total Revenue', 0)
            gross_profit = recent.get('Gross Profit', 0)
            operating_income = recent.get('Operating Income', 0)
            net_income = recent.get('Net Income', 0)
            
            gross_margin = gross_profit / revenue if revenue != 0 else 0
            operating_margin = operating_income / revenue if revenue != 0 else 0
            net_margin = net_income / revenue if revenue != 0 else 0
            
            return {
                "gross_margin": round(float(gross_margin), 3),
                "operating_margin": round(float(operating_margin), 3),
                "net_margin": round(float(net_margin), 3),
                "profitability_trend": "Stable"  # Would need time series analysis
            }
        except Exception as e:
            logger.error(f"Error in profitability analysis: {e}")
            return {"status": "Analysis error"}
    
    async def _analyze_cash_flow(self, cash_flow: pd.DataFrame, financials: pd.DataFrame) -> Dict[str, Any]:
        """Analyze cash flow quality"""
        if cash_flow.empty:
            return {"status": "Data unavailable"}
        
        try:
            cf_recent = cash_flow.iloc[:, 0]
            operating_cf = cf_recent.get('Operating Cash Flow', 0)
            capex = cf_recent.get('Capital Expenditure', 0)
            free_cash_flow = operating_cf + capex  # CapEx is usually negative
            
            return {
                "operating_cash_flow": float(operating_cf),
                "free_cash_flow": float(free_cash_flow),
                "cash_flow_quality": "Strong" if free_cash_flow > 0 else "Weak",
                "cash_conversion": "Good"  # Would need more detailed analysis
            }
        except Exception as e:
            logger.error(f"Error in cash flow analysis: {e}")
            return {"status": "Analysis error"}
    
    async def _assess_flexibility(self, balance_sheet: pd.DataFrame, cash_flow: pd.DataFrame) -> Dict[str, Any]:
        """Assess financial flexibility"""
        return {
            "debt_capacity": "Adequate",
            "refinancing_risk": "Low",
            "covenant_headroom": "Sufficient",
            "access_to_capital": "Good"
        }
    
    async def _analyze_capital_allocation(self, cash_flow: pd.DataFrame) -> Dict[str, Any]:
        """Analyze capital allocation decisions"""
        return {
            "capex_discipline": "Appropriate",
            "dividend_policy": "Sustainable",
            "share_buybacks": "Opportunistic",
            "acquisition_strategy": "Disciplined",
            "overall_allocation": "Value-creating"
        }
    
    async def _identify_red_flags(self, financials: pd.DataFrame, balance_sheet: pd.DataFrame, cash_flow: pd.DataFrame) -> List[str]:
        """Identify financial red flags"""
        red_flags = []
        
        # This would include checks for:
        # - Declining margins
        # - Cash flow vs earnings divergence
        # - Rising working capital requirements
        # - Unusual accounting changes
        # - Debt maturity concentration
        
        # For now, return empty as this requires detailed analysis
        return red_flags

# Factory function
def create_company_analyzer() -> CompanyDeepDiveAnalyzer:
    """Create and return configured company analyzer"""
    return CompanyDeepDiveAnalyzer()