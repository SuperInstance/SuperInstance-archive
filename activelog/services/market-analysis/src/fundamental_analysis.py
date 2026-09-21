import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
import requests
from bs4 import BeautifulSoup
import logging

from .models import (SecurityData, FundamentalMetrics, AnalystRating, 
                    InsiderTrading, EarningsData, CompanyProfile, ESGScoring)

logger = logging.getLogger(__name__)

class FundamentalAnalyzer:
    def __init__(self, alpha_vantage_key: Optional[str] = None):
        self.alpha_vantage_key = alpha_vantage_key
        self.session = requests.Session()
        
    def get_security_data(self, symbol: str) -> SecurityData:
        """Get basic security information"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return SecurityData(
                symbol=symbol.upper(),
                name=info.get('longName', symbol),
                asset_type=self._determine_asset_type(info),
                exchange=info.get('exchange', 'UNKNOWN'),
                sector=info.get('sector'),
                industry=info.get('industry'),
                market_cap=Decimal(str(info.get('marketCap', 0))) if info.get('marketCap') else None,
                current_price=Decimal(str(info.get('currentPrice', 0))) if info.get('currentPrice') else Decimal('0'),
                currency=info.get('currency', 'USD')
            )
        except Exception as e:
            logger.error(f"Error fetching security data for {symbol}: {e}")
            raise
    
    def calculate_fundamental_metrics(self, symbol: str) -> FundamentalMetrics:
        """Calculate comprehensive fundamental metrics"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            financials = ticker.financials
            balance_sheet = ticker.balance_sheet
            cashflow = ticker.cashflow
            
            # Get quarterly data for growth calculations
            quarterly_financials = ticker.quarterly_financials
            
            metrics = FundamentalMetrics(symbol=symbol.upper())
            
            # Valuation Ratios
            metrics.pe_ratio = self._safe_decimal(info.get('trailingPE'))
            metrics.pb_ratio = self._safe_decimal(info.get('priceToBook'))
            metrics.peg_ratio = self._safe_decimal(info.get('pegRatio'))
            metrics.ps_ratio = self._safe_decimal(info.get('priceToSalesTrailing12Months'))
            metrics.pcf_ratio = self._calculate_pcf_ratio(info, cashflow)
            metrics.ev_ebitda = self._safe_decimal(info.get('enterpriseToEbitda'))
            
            # Growth Metrics
            metrics.revenue_growth_yoy = self._calculate_revenue_growth(financials)
            metrics.earnings_growth_yoy = self._calculate_earnings_growth(financials)
            metrics.revenue_growth_3y = self._calculate_multi_year_growth(financials, 'Total Revenue', 3)
            metrics.earnings_growth_3y = self._calculate_multi_year_growth(financials, 'Net Income', 3)
            
            # Profitability Metrics
            metrics.gross_margin = self._safe_decimal(info.get('grossMargins'))
            metrics.operating_margin = self._safe_decimal(info.get('operatingMargins'))
            metrics.net_margin = self._safe_decimal(info.get('profitMargins'))
            metrics.roe = self._safe_decimal(info.get('returnOnEquity'))
            metrics.roa = self._safe_decimal(info.get('returnOnAssets'))
            metrics.roic = self._calculate_roic(financials, balance_sheet)
            
            # Financial Health
            metrics.debt_to_equity = self._safe_decimal(info.get('debtToEquity'))
            metrics.current_ratio = self._safe_decimal(info.get('currentRatio'))
            metrics.quick_ratio = self._safe_decimal(info.get('quickRatio'))
            metrics.interest_coverage = self._calculate_interest_coverage(financials)
            
            # Dividend Metrics
            metrics.dividend_yield = self._safe_decimal(info.get('dividendYield'))
            metrics.dividend_payout_ratio = self._safe_decimal(info.get('payoutRatio'))
            metrics.dividend_growth_rate = self._calculate_dividend_growth(ticker)
            
            # Cash Flow Metrics
            if not cashflow.empty:
                latest_cashflow = cashflow.iloc[:, 0]
                metrics.operating_cash_flow = self._safe_decimal(latest_cashflow.get('Total Cash From Operating Activities'))
                metrics.free_cash_flow = self._calculate_free_cash_flow(cashflow)
                metrics.fcf_yield = self._calculate_fcf_yield(info, cashflow)
            
            # Per Share Metrics
            metrics.book_value_per_share = self._safe_decimal(info.get('bookValue'))
            metrics.earnings_per_share = self._safe_decimal(info.get('trailingEps'))
            metrics.revenue_per_share = self._calculate_revenue_per_share(financials, info)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating fundamental metrics for {symbol}: {e}")
            raise
    
    def get_analyst_ratings(self, symbol: str) -> List[AnalystRating]:
        """Get analyst ratings and price targets"""
        try:
            ticker = yf.Ticker(symbol)
            recommendations = ticker.recommendations
            
            if recommendations is None or recommendations.empty:
                return []
            
            ratings = []
            for _, row in recommendations.tail(10).iterrows():  # Get latest 10 ratings
                rating = AnalystRating(
                    symbol=symbol.upper(),
                    analyst_firm=row.get('Firm', 'Unknown'),
                    rating=self._map_rating(row.get('To Grade', '')),
                    previous_rating=self._map_rating(row.get('From Grade', '')) if row.get('From Grade') else None,
                    rating_change_date=row.name if hasattr(row, 'name') else datetime.now()
                )
                ratings.append(rating)
            
            return ratings
            
        except Exception as e:
            logger.error(f"Error fetching analyst ratings for {symbol}: {e}")
            return []
    
    def get_insider_trading(self, symbol: str) -> List[InsiderTrading]:
        """Get insider trading information"""
        try:
            ticker = yf.Ticker(symbol)
            insider_transactions = ticker.insider_transactions
            
            if insider_transactions is None or insider_transactions.empty:
                return []
            
            transactions = []
            for _, row in insider_transactions.iterrows():
                transaction = InsiderTrading(
                    symbol=symbol.upper(),
                    insider_name=row.get('Insider', 'Unknown'),
                    position=row.get('Position', 'Unknown'),
                    transaction_type=row.get('Transaction', 'Unknown'),
                    shares=Decimal(str(row.get('Shares', 0))),
                    price=Decimal(str(row.get('Price', 0))),
                    value=Decimal(str(row.get('Value', 0))),
                    transaction_date=row.get('Date', datetime.now().date()),
                    filing_date=row.get('Date', datetime.now().date()),
                    ownership_after=Decimal(str(row.get('Shares Owned After', 0))) if row.get('Shares Owned After') else None
                )
                transactions.append(transaction)
            
            return transactions
            
        except Exception as e:
            logger.error(f"Error fetching insider trading for {symbol}: {e}")
            return []
    
    def get_earnings_data(self, symbol: str) -> List[EarningsData]:
        """Get earnings history and estimates"""
        try:
            ticker = yf.Ticker(symbol)
            earnings_history = ticker.earnings_dates
            
            if earnings_history is None or earnings_history.empty:
                return []
            
            earnings_list = []
            for date, row in earnings_history.head(12).iterrows():  # Get last 12 quarters
                earnings = EarningsData(
                    symbol=symbol.upper(),
                    quarter=self._determine_quarter(date),
                    fiscal_year=date.year,
                    earnings_date=date.date(),
                    eps_actual=self._safe_decimal(row.get('EPS Estimate')),
                    eps_estimate=self._safe_decimal(row.get('EPS Estimate')),
                    revenue_actual=self._safe_decimal(row.get('Revenue Estimate')),
                    revenue_estimate=self._safe_decimal(row.get('Revenue Estimate'))
                )
                earnings_list.append(earnings)
            
            return earnings_list
            
        except Exception as e:
            logger.error(f"Error fetching earnings data for {symbol}: {e}")
            return []
    
    def get_company_profile(self, symbol: str) -> CompanyProfile:
        """Get comprehensive company profile"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            profile = CompanyProfile(
                symbol=symbol.upper(),
                company_name=info.get('longName', symbol),
                description=info.get('longBusinessSummary', 'No description available'),
                industry=info.get('industry', 'Unknown'),
                sector=info.get('sector', 'Unknown'),
                country=info.get('country', 'Unknown'),
                website=info.get('website'),
                headquarters=f"{info.get('city', '')}, {info.get('state', '')}, {info.get('country', '')}".strip(', '),
                founded_year=None,  # Not available in yfinance
                employees=info.get('fullTimeEmployees'),
                ceo=None,  # Would need to scrape or use additional API
                business_model=self._extract_business_model(info.get('longBusinessSummary', '')),
                competitive_advantages=self._extract_competitive_advantages(info.get('longBusinessSummary', '')),
                key_risks=self._extract_key_risks(info.get('longBusinessSummary', ''))
            )
            
            return profile
            
        except Exception as e:
            logger.error(f"Error fetching company profile for {symbol}: {e}")
            raise
    
    def calculate_esg_scoring(self, symbol: str) -> ESGScoring:
        """Calculate ESG scoring (simplified version)"""
        try:
            ticker = yf.Ticker(symbol)
            sustainability = ticker.sustainability
            
            esg = ESGScoring(symbol=symbol.upper())
            
            if sustainability is not None and not sustainability.empty:
                # yfinance provides some ESG data
                esg_scores = sustainability.T
                if 'totalEsg' in esg_scores.columns:
                    esg.total_esg_score = self._safe_decimal(esg_scores['totalEsg'].iloc[0])
                if 'environmentScore' in esg_scores.columns:
                    esg.environmental_score = self._safe_decimal(esg_scores['environmentScore'].iloc[0])
                if 'socialScore' in esg_scores.columns:
                    esg.social_score = self._safe_decimal(esg_scores['socialScore'].iloc[0])
                if 'governanceScore' in esg_scores.columns:
                    esg.governance_score = self._safe_decimal(esg_scores['governanceScore'].iloc[0])
            
            # Calculate synthetic ESG rating
            if esg.total_esg_score:
                esg.esg_rating = self._calculate_esg_rating(esg.total_esg_score)
            
            return esg
            
        except Exception as e:
            logger.error(f"Error calculating ESG scoring for {symbol}: {e}")
            return ESGScoring(symbol=symbol.upper())
    
    def analyze_financial_health(self, symbol: str) -> Dict[str, Any]:
        """Comprehensive financial health analysis"""
        try:
            metrics = self.calculate_fundamental_metrics(symbol)
            
            health_score = 0
            max_score = 100
            analysis = {}
            
            # Profitability Analysis (25 points)
            profitability_score = 0
            if metrics.roe and metrics.roe > 0.15:  # ROE > 15%
                profitability_score += 10
            elif metrics.roe and metrics.roe > 0.10:  # ROE > 10%
                profitability_score += 5
            
            if metrics.net_margin and metrics.net_margin > 0.20:  # Net margin > 20%
                profitability_score += 10
            elif metrics.net_margin and metrics.net_margin > 0.10:  # Net margin > 10%
                profitability_score += 5
            
            if metrics.roic and metrics.roic > 0.15:  # ROIC > 15%
                profitability_score += 5
            
            health_score += profitability_score
            analysis['profitability_score'] = profitability_score
            analysis['profitability_grade'] = self._score_to_grade(profitability_score, 25)
            
            # Financial Stability (25 points)
            stability_score = 0
            if metrics.debt_to_equity and metrics.debt_to_equity < 0.3:  # Low debt
                stability_score += 10
            elif metrics.debt_to_equity and metrics.debt_to_equity < 0.6:  # Moderate debt
                stability_score += 5
            
            if metrics.current_ratio and metrics.current_ratio > 2.0:  # Strong liquidity
                stability_score += 10
            elif metrics.current_ratio and metrics.current_ratio > 1.5:  # Adequate liquidity
                stability_score += 5
            
            if metrics.interest_coverage and metrics.interest_coverage > 5:  # Strong interest coverage
                stability_score += 5
            
            health_score += stability_score
            analysis['stability_score'] = stability_score
            analysis['stability_grade'] = self._score_to_grade(stability_score, 25)
            
            # Growth (25 points)
            growth_score = 0
            if metrics.revenue_growth_yoy and metrics.revenue_growth_yoy > 0.20:  # Revenue growth > 20%
                growth_score += 10
            elif metrics.revenue_growth_yoy and metrics.revenue_growth_yoy > 0.10:  # Revenue growth > 10%
                growth_score += 5
            
            if metrics.earnings_growth_yoy and metrics.earnings_growth_yoy > 0.25:  # Earnings growth > 25%
                growth_score += 10
            elif metrics.earnings_growth_yoy and metrics.earnings_growth_yoy > 0.15:  # Earnings growth > 15%
                growth_score += 5
            
            if metrics.revenue_growth_3y and metrics.revenue_growth_3y > 0.15:  # 3-year growth > 15%
                growth_score += 5
            
            health_score += growth_score
            analysis['growth_score'] = growth_score
            analysis['growth_grade'] = self._score_to_grade(growth_score, 25)
            
            # Valuation (25 points)
            valuation_score = 0
            if metrics.pe_ratio and metrics.pe_ratio < 15:  # Low P/E
                valuation_score += 10
            elif metrics.pe_ratio and metrics.pe_ratio < 25:  # Reasonable P/E
                valuation_score += 5
            
            if metrics.pb_ratio and metrics.pb_ratio < 1.5:  # Low P/B
                valuation_score += 10
            elif metrics.pb_ratio and metrics.pb_ratio < 3:  # Reasonable P/B
                valuation_score += 5
            
            if metrics.peg_ratio and metrics.peg_ratio < 1:  # PEG < 1
                valuation_score += 5
            
            health_score += valuation_score
            analysis['valuation_score'] = valuation_score
            analysis['valuation_grade'] = self._score_to_grade(valuation_score, 25)
            
            # Overall analysis
            analysis['total_score'] = health_score
            analysis['overall_grade'] = self._score_to_grade(health_score, max_score)
            analysis['health_rating'] = self._health_rating(health_score, max_score)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing financial health for {symbol}: {e}")
            raise
    
    # Helper Methods
    def _determine_asset_type(self, info: Dict) -> str:
        """Determine asset type from ticker info"""
        if info.get('quoteType') == 'ETF':
            return 'etf'
        elif info.get('quoteType') == 'EQUITY':
            return 'stock'
        else:
            return 'stock'  # Default
    
    def _safe_decimal(self, value: Any) -> Optional[Decimal]:
        """Safely convert value to Decimal"""
        if value is None or pd.isna(value):
            return None
        try:
            return Decimal(str(value))
        except:
            return None
    
    def _calculate_pcf_ratio(self, info: Dict, cashflow: pd.DataFrame) -> Optional[Decimal]:
        """Calculate Price-to-Cash Flow ratio"""
        try:
            market_cap = info.get('marketCap')
            if market_cap and not cashflow.empty:
                operating_cf = cashflow.iloc[:, 0].get('Total Cash From Operating Activities')
                if operating_cf and operating_cf != 0:
                    return Decimal(str(market_cap / operating_cf))
        except:
            pass
        return None
    
    def _calculate_revenue_growth(self, financials: pd.DataFrame) -> Optional[Decimal]:
        """Calculate year-over-year revenue growth"""
        try:
            if not financials.empty and len(financials.columns) >= 2:
                current_revenue = financials.loc['Total Revenue'].iloc[0]
                previous_revenue = financials.loc['Total Revenue'].iloc[1]
                if previous_revenue and previous_revenue != 0:
                    growth = (current_revenue - previous_revenue) / abs(previous_revenue)
                    return Decimal(str(growth))
        except:
            pass
        return None
    
    def _calculate_earnings_growth(self, financials: pd.DataFrame) -> Optional[Decimal]:
        """Calculate year-over-year earnings growth"""
        try:
            if not financials.empty and len(financials.columns) >= 2:
                current_earnings = financials.loc['Net Income'].iloc[0]
                previous_earnings = financials.loc['Net Income'].iloc[1]
                if previous_earnings and previous_earnings != 0:
                    growth = (current_earnings - previous_earnings) / abs(previous_earnings)
                    return Decimal(str(growth))
        except:
            pass
        return None
    
    def _calculate_multi_year_growth(self, financials: pd.DataFrame, metric: str, years: int) -> Optional[Decimal]:
        """Calculate multi-year compound annual growth rate"""
        try:
            if not financials.empty and len(financials.columns) >= years:
                current_value = financials.loc[metric].iloc[0]
                past_value = financials.loc[metric].iloc[years-1]
                if past_value and past_value != 0:
                    cagr = ((current_value / past_value) ** (1/years)) - 1
                    return Decimal(str(cagr))
        except:
            pass
        return None
    
    def _calculate_roic(self, financials: pd.DataFrame, balance_sheet: pd.DataFrame) -> Optional[Decimal]:
        """Calculate Return on Invested Capital"""
        try:
            if not financials.empty and not balance_sheet.empty:
                net_income = financials.loc['Net Income'].iloc[0]
                total_debt = balance_sheet.loc['Total Debt'].iloc[0] if 'Total Debt' in balance_sheet.index else 0
                shareholders_equity = balance_sheet.loc['Stockholders Equity'].iloc[0] if 'Stockholders Equity' in balance_sheet.index else 0
                
                invested_capital = total_debt + shareholders_equity
                if invested_capital and invested_capital != 0:
                    return Decimal(str(net_income / invested_capital))
        except:
            pass
        return None
    
    def _calculate_interest_coverage(self, financials: pd.DataFrame) -> Optional[Decimal]:
        """Calculate interest coverage ratio"""
        try:
            if not financials.empty:
                ebit = financials.loc['EBIT'].iloc[0] if 'EBIT' in financials.index else None
                interest_expense = financials.loc['Interest Expense'].iloc[0] if 'Interest Expense' in financials.index else None
                
                if ebit and interest_expense and interest_expense != 0:
                    return Decimal(str(abs(ebit / interest_expense)))
        except:
            pass
        return None
    
    def _calculate_dividend_growth(self, ticker) -> Optional[Decimal]:
        """Calculate dividend growth rate"""
        try:
            dividends = ticker.dividends
            if len(dividends) >= 2:
                # Get annual dividends for the last two years
                recent_div = dividends.resample('Y').sum().iloc[-1]
                previous_div = dividends.resample('Y').sum().iloc[-2]
                
                if previous_div and previous_div != 0:
                    growth = (recent_div - previous_div) / previous_div
                    return Decimal(str(growth))
        except:
            pass
        return None
    
    def _calculate_free_cash_flow(self, cashflow: pd.DataFrame) -> Optional[Decimal]:
        """Calculate free cash flow"""
        try:
            if not cashflow.empty:
                operating_cf = cashflow.iloc[:, 0].get('Total Cash From Operating Activities', 0)
                capex = cashflow.iloc[:, 0].get('Capital Expenditures', 0)
                
                if operating_cf is not None and capex is not None:
                    fcf = operating_cf + capex  # capex is usually negative
                    return Decimal(str(fcf))
        except:
            pass
        return None
    
    def _calculate_fcf_yield(self, info: Dict, cashflow: pd.DataFrame) -> Optional[Decimal]:
        """Calculate free cash flow yield"""
        try:
            market_cap = info.get('marketCap')
            fcf = self._calculate_free_cash_flow(cashflow)
            
            if market_cap and fcf and market_cap != 0:
                return Decimal(str(fcf / market_cap))
        except:
            pass
        return None
    
    def _calculate_revenue_per_share(self, financials: pd.DataFrame, info: Dict) -> Optional[Decimal]:
        """Calculate revenue per share"""
        try:
            if not financials.empty:
                revenue = financials.loc['Total Revenue'].iloc[0]
                shares_outstanding = info.get('sharesOutstanding')
                
                if revenue and shares_outstanding and shares_outstanding != 0:
                    return Decimal(str(revenue / shares_outstanding))
        except:
            pass
        return None
    
    def _map_rating(self, rating_text: str) -> str:
        """Map analyst rating text to standard format"""
        rating_text = rating_text.lower()
        if 'strong buy' in rating_text or 'outperform' in rating_text:
            return 'strong_buy'
        elif 'buy' in rating_text or 'overweight' in rating_text:
            return 'buy'
        elif 'hold' in rating_text or 'neutral' in rating_text:
            return 'hold'
        elif 'sell' in rating_text or 'underweight' in rating_text:
            return 'sell'
        elif 'strong sell' in rating_text or 'underperform' in rating_text:
            return 'strong_sell'
        else:
            return 'hold'
    
    def _determine_quarter(self, date: datetime) -> str:
        """Determine quarter from date"""
        quarter = (date.month - 1) // 3 + 1
        return f"Q{quarter} {date.year}"
    
    def _extract_business_model(self, description: str) -> str:
        """Extract business model from company description"""
        # Simplified keyword-based extraction
        description_lower = description.lower()
        if 'software' in description_lower and 'service' in description_lower:
            return 'SaaS'
        elif 'subscription' in description_lower:
            return 'Subscription'
        elif 'marketplace' in description_lower:
            return 'Marketplace'
        elif 'retail' in description_lower:
            return 'Retail'
        elif 'manufacturing' in description_lower:
            return 'Manufacturing'
        else:
            return 'Traditional'
    
    def _extract_competitive_advantages(self, description: str) -> List[str]:
        """Extract competitive advantages from description"""
        advantages = []
        description_lower = description.lower()
        
        advantage_keywords = {
            'brand': ['brand', 'trademark', 'reputation'],
            'technology': ['technology', 'innovation', 'proprietary', 'patent'],
            'scale': ['scale', 'size', 'largest', 'leading'],
            'network': ['network', 'platform', 'ecosystem'],
            'data': ['data', 'analytics', 'insights'],
            'cost': ['cost', 'efficiency', 'lean']
        }
        
        for advantage, keywords in advantage_keywords.items():
            if any(keyword in description_lower for keyword in keywords):
                advantages.append(advantage)
        
        return advantages[:5]  # Limit to top 5
    
    def _extract_key_risks(self, description: str) -> List[str]:
        """Extract key risks from description"""
        risks = []
        description_lower = description.lower()
        
        risk_keywords = {
            'competition': ['competition', 'competitive', 'rival'],
            'regulation': ['regulation', 'regulatory', 'government', 'compliance'],
            'technology': ['technology risk', 'obsolescence', 'disruption'],
            'market': ['market risk', 'demand', 'cyclical'],
            'operational': ['operational', 'supply chain', 'operations']
        }
        
        for risk, keywords in risk_keywords.items():
            if any(keyword in description_lower for keyword in keywords):
                risks.append(risk)
        
        return risks[:5]  # Limit to top 5
    
    def _calculate_esg_rating(self, score: Decimal) -> str:
        """Calculate ESG rating from score"""
        score_float = float(score)
        if score_float >= 90:
            return 'AAA'
        elif score_float >= 80:
            return 'AA'
        elif score_float >= 70:
            return 'A'
        elif score_float >= 60:
            return 'BBB'
        elif score_float >= 50:
            return 'BB'
        elif score_float >= 40:
            return 'B'
        else:
            return 'CCC'
    
    def _score_to_grade(self, score: float, max_score: float) -> str:
        """Convert numeric score to letter grade"""
        percentage = (score / max_score) * 100
        if percentage >= 90:
            return 'A+'
        elif percentage >= 85:
            return 'A'
        elif percentage >= 80:
            return 'A-'
        elif percentage >= 75:
            return 'B+'
        elif percentage >= 70:
            return 'B'
        elif percentage >= 65:
            return 'B-'
        elif percentage >= 60:
            return 'C+'
        elif percentage >= 55:
            return 'C'
        elif percentage >= 50:
            return 'C-'
        elif percentage >= 40:
            return 'D'
        else:
            return 'F'
    
    def _health_rating(self, score: float, max_score: float) -> str:
        """Convert health score to rating"""
        percentage = (score / max_score) * 100
        if percentage >= 80:
            return 'Excellent'
        elif percentage >= 60:
            return 'Good'
        elif percentage >= 40:
            return 'Fair'
        elif percentage >= 20:
            return 'Poor'
        else:
            return 'Very Poor'