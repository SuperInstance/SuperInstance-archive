"""
Economic Scenario Planning Module

This module provides comprehensive economic scenario planning and analysis capabilities.
Includes macroeconomic modeling, market simulation, financial risk assessment, and 
economic impact analysis for various scenarios and policy decisions.

Key Features:
- Macroeconomic indicator modeling (GDP, inflation, unemployment, etc.)
- Market dynamics simulation (supply/demand, pricing, competition)
- Financial system modeling (banking, credit, investment flows)
- Policy impact analysis (fiscal, monetary, regulatory)
- Economic shock simulation (recession, market crash, pandemic)
- Regional and sector-specific economic modeling
- Monte Carlo economic forecasting
- Economic multiplier analysis
- Business cycle modeling
- International trade and currency modeling
"""

import asyncio
import logging
import random
import time
import json
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from enum import Enum
from collections import defaultdict, deque
import math


class EconomicIndicator(Enum):
    """Economic indicators"""
    GDP = "gdp"
    INFLATION = "inflation"
    UNEMPLOYMENT = "unemployment"
    INTEREST_RATE = "interest_rate"
    EXCHANGE_RATE = "exchange_rate"
    STOCK_INDEX = "stock_index"
    CONSUMER_CONFIDENCE = "consumer_confidence"
    BUSINESS_CONFIDENCE = "business_confidence"
    RETAIL_SALES = "retail_sales"
    INDUSTRIAL_PRODUCTION = "industrial_production"
    HOUSING_STARTS = "housing_starts"
    TRADE_BALANCE = "trade_balance"
    GOVERNMENT_DEBT = "government_debt"
    CONSUMER_DEBT = "consumer_debt"
    MONEY_SUPPLY = "money_supply"


class EconomicSector(Enum):
    """Economic sectors"""
    AGRICULTURE = "agriculture"
    MINING = "mining"
    MANUFACTURING = "manufacturing"
    UTILITIES = "utilities"
    CONSTRUCTION = "construction"
    WHOLESALE = "wholesale"
    RETAIL = "retail"
    TRANSPORTATION = "transportation"
    INFORMATION = "information"
    FINANCE = "finance"
    REAL_ESTATE = "real_estate"
    PROFESSIONAL = "professional"
    MANAGEMENT = "management"
    ADMINISTRATIVE = "administrative"
    EDUCATION = "education"
    HEALTHCARE = "healthcare"
    ARTS = "arts"
    ACCOMMODATION = "accommodation"
    OTHER_SERVICES = "other_services"
    PUBLIC_ADMIN = "public_admin"


class PolicyType(Enum):
    """Policy intervention types"""
    FISCAL_EXPANSION = "fiscal_expansion"
    FISCAL_CONTRACTION = "fiscal_contraction"
    MONETARY_EXPANSION = "monetary_expansion"
    MONETARY_CONTRACTION = "monetary_contraction"
    TAX_CUT = "tax_cut"
    TAX_INCREASE = "tax_increase"
    SPENDING_INCREASE = "spending_increase"
    SPENDING_CUT = "spending_cut"
    REGULATION_INCREASE = "regulation_increase"
    REGULATION_DECREASE = "regulation_decrease"
    TRADE_LIBERALIZATION = "trade_liberalization"
    TRADE_PROTECTION = "trade_protection"


class EconomicShock(Enum):
    """Types of economic shocks"""
    RECESSION = "recession"
    FINANCIAL_CRISIS = "financial_crisis"
    PANDEMIC = "pandemic"
    NATURAL_DISASTER = "natural_disaster"
    ENERGY_CRISIS = "energy_crisis"
    TECHNOLOGY_DISRUPTION = "technology_disruption"
    GEOPOLITICAL_CRISIS = "geopolitical_crisis"
    SUPPLY_CHAIN_DISRUPTION = "supply_chain_disruption"
    CURRENCY_CRISIS = "currency_crisis"
    INFLATION_SPIKE = "inflation_spike"
    MARKET_CRASH = "market_crash"
    COMMODITY_SHOCK = "commodity_shock"


@dataclass
class EconomicData:
    """Economic data point"""
    indicator: EconomicIndicator
    value: float
    period: datetime
    region: str = "national"
    sector: Optional[EconomicSector] = None
    confidence_interval: Tuple[float, float] = (0.0, 0.0)
    source: str = "simulation"


@dataclass
class EconomicScenario:
    """Economic scenario definition"""
    name: str
    description: str
    duration_months: int
    initial_conditions: Dict[EconomicIndicator, float]
    shocks: List[Tuple[EconomicShock, int, float]]  # (shock_type, month, intensity)
    policies: List[Tuple[PolicyType, int, float]]  # (policy_type, month, intensity)
    probability: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SectorImpact:
    """Sector-specific economic impact"""
    sector: EconomicSector
    gdp_impact: float  # Percentage change
    employment_impact: float  # Percentage change
    productivity_impact: float  # Percentage change
    investment_impact: float  # Percentage change
    recovery_months: int
    confidence_level: float


@dataclass
class PolicyImpact:
    """Policy intervention impact"""
    policy_type: PolicyType
    indicator_impacts: Dict[EconomicIndicator, float]
    sector_impacts: Dict[EconomicSector, float]
    time_to_effect: int  # months
    duration_months: int
    fiscal_cost: float
    effectiveness_score: float


class EconomicModel(ABC):
    """Abstract base class for economic models"""
    
    @abstractmethod
    def simulate(self, months: int, scenario: EconomicScenario) -> Dict[EconomicIndicator, List[float]]:
        """Simulate economic indicators over time"""
        pass
    
    @abstractmethod
    def analyze_shock(self, shock: EconomicShock, intensity: float) -> Dict[EconomicIndicator, float]:
        """Analyze the impact of an economic shock"""
        pass
    
    @abstractmethod
    def evaluate_policy(self, policy: PolicyType, intensity: float) -> PolicyImpact:
        """Evaluate the impact of a policy intervention"""
        pass


class MacroeconomicModel(EconomicModel):
    """Macroeconomic modeling using simplified IS-LM framework"""
    
    def __init__(self, country: str = "default"):
        self.country = country
        self.multipliers = self._initialize_multipliers()
        self.elasticities = self._initialize_elasticities()
        self.trend_growth = 2.5  # Annual GDP growth trend
        self.natural_unemployment = 5.0  # Natural unemployment rate
        self.inflation_target = 2.0  # Target inflation rate
        
    def _initialize_multipliers(self) -> Dict[str, float]:
        """Initialize economic multipliers"""
        return {
            'fiscal_multiplier': 1.2,
            'monetary_multiplier': 0.8,
            'investment_multiplier': 1.5,
            'export_multiplier': 1.3,
            'consumption_multiplier': 0.9
        }
    
    def _initialize_elasticities(self) -> Dict[str, float]:
        """Initialize economic elasticities"""
        return {
            'gdp_inflation': 0.3,
            'unemployment_inflation': -0.5,  # Phillips curve
            'gdp_interest': -0.4,
            'investment_interest': -0.8,
            'consumption_income': 0.7,
            'imports_gdp': 1.2
        }
    
    def simulate(self, months: int, scenario: EconomicScenario) -> Dict[EconomicIndicator, List[float]]:
        """Simulate macroeconomic indicators"""
        results = defaultdict(list)
        
        # Initialize values
        current_values = dict(scenario.initial_conditions)
        
        for month in range(months):
            # Apply trend growth
            if EconomicIndicator.GDP in current_values:
                current_values[EconomicIndicator.GDP] *= (1 + self.trend_growth / 1200)  # Monthly growth
            
            # Apply shocks
            for shock_type, shock_month, intensity in scenario.shocks:
                if month == shock_month:
                    shock_impacts = self.analyze_shock(shock_type, intensity)
                    for indicator, impact in shock_impacts.items():
                        if indicator in current_values:
                            current_values[indicator] *= (1 + impact / 100)
            
            # Apply policies
            for policy_type, policy_month, intensity in scenario.policies:
                if month >= policy_month:
                    policy_impact = self.evaluate_policy(policy_type, intensity)
                    for indicator, impact in policy_impact.indicator_impacts.items():
                        if indicator in current_values:
                            # Gradual policy impact
                            months_since = month - policy_month + 1
                            effect_factor = min(1.0, months_since / policy_impact.time_to_effect)
                            current_values[indicator] += impact * effect_factor / 100
            
            # Apply economic relationships
            current_values = self._apply_economic_relationships(current_values)
            
            # Store results
            for indicator, value in current_values.items():
                results[indicator].append(value)
            
            # Add some random noise
            for indicator in current_values:
                noise = random.gauss(0, 0.1)  # 0.1% standard deviation
                current_values[indicator] *= (1 + noise / 100)
        
        return dict(results)
    
    def analyze_shock(self, shock: EconomicShock, intensity: float) -> Dict[EconomicIndicator, float]:
        """Analyze economic shock impacts"""
        impacts = {}
        
        if shock == EconomicShock.RECESSION:
            impacts = {
                EconomicIndicator.GDP: -2.0 * intensity,
                EconomicIndicator.UNEMPLOYMENT: 1.5 * intensity,
                EconomicIndicator.INFLATION: -0.5 * intensity,
                EconomicIndicator.CONSUMER_CONFIDENCE: -10 * intensity,
                EconomicIndicator.BUSINESS_CONFIDENCE: -12 * intensity,
                EconomicIndicator.STOCK_INDEX: -15 * intensity
            }
        elif shock == EconomicShock.FINANCIAL_CRISIS:
            impacts = {
                EconomicIndicator.GDP: -3.5 * intensity,
                EconomicIndicator.UNEMPLOYMENT: 2.5 * intensity,
                EconomicIndicator.STOCK_INDEX: -25 * intensity,
                EconomicIndicator.CONSUMER_CONFIDENCE: -15 * intensity,
                EconomicIndicator.INTEREST_RATE: 1.0 * intensity,
                EconomicIndicator.CONSUMER_DEBT: -5 * intensity
            }
        elif shock == EconomicShock.PANDEMIC:
            impacts = {
                EconomicIndicator.GDP: -4.0 * intensity,
                EconomicIndicator.UNEMPLOYMENT: 3.0 * intensity,
                EconomicIndicator.RETAIL_SALES: -20 * intensity,
                EconomicIndicator.INDUSTRIAL_PRODUCTION: -15 * intensity,
                EconomicIndicator.CONSUMER_CONFIDENCE: -20 * intensity
            }
        elif shock == EconomicShock.INFLATION_SPIKE:
            impacts = {
                EconomicIndicator.INFLATION: 3.0 * intensity,
                EconomicIndicator.CONSUMER_CONFIDENCE: -8 * intensity,
                EconomicIndicator.RETAIL_SALES: -5 * intensity,
                EconomicIndicator.INTEREST_RATE: 1.5 * intensity
            }
        elif shock == EconomicShock.ENERGY_CRISIS:
            impacts = {
                EconomicIndicator.INFLATION: 2.0 * intensity,
                EconomicIndicator.GDP: -1.5 * intensity,
                EconomicIndicator.INDUSTRIAL_PRODUCTION: -8 * intensity,
                EconomicIndicator.CONSUMER_CONFIDENCE: -6 * intensity
            }
        elif shock == EconomicShock.MARKET_CRASH:
            impacts = {
                EconomicIndicator.STOCK_INDEX: -30 * intensity,
                EconomicIndicator.CONSUMER_CONFIDENCE: -12 * intensity,
                EconomicIndicator.BUSINESS_CONFIDENCE: -15 * intensity,
                EconomicIndicator.RETAIL_SALES: -8 * intensity
            }
        elif shock == EconomicShock.SUPPLY_CHAIN_DISRUPTION:
            impacts = {
                EconomicIndicator.INFLATION: 1.5 * intensity,
                EconomicIndicator.INDUSTRIAL_PRODUCTION: -10 * intensity,
                EconomicIndicator.TRADE_BALANCE: -5 * intensity,
                EconomicIndicator.GDP: -1.0 * intensity
            }
        elif shock == EconomicShock.CURRENCY_CRISIS:
            impacts = {
                EconomicIndicator.EXCHANGE_RATE: 20 * intensity,  # Depreciation
                EconomicIndicator.INFLATION: 2.5 * intensity,
                EconomicIndicator.INTEREST_RATE: 3.0 * intensity,
                EconomicIndicator.GDP: -2.0 * intensity
            }
        elif shock == EconomicShock.GEOPOLITICAL_CRISIS:
            impacts = {
                EconomicIndicator.STOCK_INDEX: -10 * intensity,
                EconomicIndicator.EXCHANGE_RATE: 5 * intensity,
                EconomicIndicator.CONSUMER_CONFIDENCE: -8 * intensity,
                EconomicIndicator.BUSINESS_CONFIDENCE: -10 * intensity
            }
        elif shock == EconomicShock.TECHNOLOGY_DISRUPTION:
            impacts = {
                EconomicIndicator.GDP: 1.0 * intensity,  # Positive long-term
                EconomicIndicator.UNEMPLOYMENT: 0.5 * intensity,  # Short-term displacement
                EconomicIndicator.INDUSTRIAL_PRODUCTION: 2.0 * intensity,
                EconomicIndicator.BUSINESS_CONFIDENCE: 5 * intensity
            }
        else:
            # Generic shock
            impacts = {
                EconomicIndicator.GDP: -1.0 * intensity,
                EconomicIndicator.CONSUMER_CONFIDENCE: -5 * intensity
            }
        
        return impacts
    
    def evaluate_policy(self, policy: PolicyType, intensity: float) -> PolicyImpact:
        """Evaluate policy intervention impact"""
        indicator_impacts = {}
        sector_impacts = {}
        time_to_effect = 3  # Default 3 months
        duration_months = 12  # Default 12 months
        fiscal_cost = 0
        effectiveness_score = 0.7
        
        if policy == PolicyType.FISCAL_EXPANSION:
            indicator_impacts = {
                EconomicIndicator.GDP: 1.2 * intensity * self.multipliers['fiscal_multiplier'],
                EconomicIndicator.UNEMPLOYMENT: -0.8 * intensity,
                EconomicIndicator.INFLATION: 0.3 * intensity,
                EconomicIndicator.GOVERNMENT_DEBT: 2.0 * intensity
            }
            fiscal_cost = intensity * 100000  # Million dollars per intensity point
            effectiveness_score = 0.8
            
        elif policy == PolicyType.FISCAL_CONTRACTION:
            indicator_impacts = {
                EconomicIndicator.GDP: -0.8 * intensity,
                EconomicIndicator.UNEMPLOYMENT: 0.6 * intensity,
                EconomicIndicator.INFLATION: -0.2 * intensity,
                EconomicIndicator.GOVERNMENT_DEBT: -1.5 * intensity
            }
            fiscal_cost = -intensity * 80000
            effectiveness_score = 0.75
            
        elif policy == PolicyType.MONETARY_EXPANSION:
            indicator_impacts = {
                EconomicIndicator.INTEREST_RATE: -0.5 * intensity,
                EconomicIndicator.GDP: 0.8 * intensity * self.multipliers['monetary_multiplier'],
                EconomicIndicator.INFLATION: 0.4 * intensity,
                EconomicIndicator.STOCK_INDEX: 5 * intensity,
                EconomicIndicator.EXCHANGE_RATE: 2 * intensity  # Depreciation
            }
            time_to_effect = 6
            effectiveness_score = 0.7
            
        elif policy == PolicyType.MONETARY_CONTRACTION:
            indicator_impacts = {
                EconomicIndicator.INTEREST_RATE: 0.5 * intensity,
                EconomicIndicator.GDP: -0.6 * intensity,
                EconomicIndicator.INFLATION: -0.3 * intensity,
                EconomicIndicator.STOCK_INDEX: -3 * intensity,
                EconomicIndicator.EXCHANGE_RATE: -1.5 * intensity  # Appreciation
            }
            time_to_effect = 4
            effectiveness_score = 0.8
            
        elif policy == PolicyType.TAX_CUT:
            indicator_impacts = {
                EconomicIndicator.GDP: 1.0 * intensity * self.multipliers['consumption_multiplier'],
                EconomicIndicator.CONSUMER_CONFIDENCE: 3 * intensity,
                EconomicIndicator.RETAIL_SALES: 2 * intensity,
                EconomicIndicator.GOVERNMENT_DEBT: 1.5 * intensity
            }
            fiscal_cost = intensity * 75000
            effectiveness_score = 0.75
            
        elif policy == PolicyType.TAX_INCREASE:
            indicator_impacts = {
                EconomicIndicator.GDP: -0.7 * intensity,
                EconomicIndicator.CONSUMER_CONFIDENCE: -2 * intensity,
                EconomicIndicator.RETAIL_SALES: -1.5 * intensity,
                EconomicIndicator.GOVERNMENT_DEBT: -1.2 * intensity
            }
            fiscal_cost = -intensity * 60000
            effectiveness_score = 0.7
            
        elif policy == PolicyType.SPENDING_INCREASE:
            indicator_impacts = {
                EconomicIndicator.GDP: 1.5 * intensity * self.multipliers['fiscal_multiplier'],
                EconomicIndicator.UNEMPLOYMENT: -1.0 * intensity,
                EconomicIndicator.GOVERNMENT_DEBT: 2.5 * intensity
            }
            sector_impacts = {
                EconomicSector.CONSTRUCTION: 3 * intensity,
                EconomicSector.MANUFACTURING: 2 * intensity,
                EconomicSector.PROFESSIONAL: 1.5 * intensity
            }
            fiscal_cost = intensity * 120000
            effectiveness_score = 0.85
            
        elif policy == PolicyType.TRADE_LIBERALIZATION:
            indicator_impacts = {
                EconomicIndicator.GDP: 0.8 * intensity,
                EconomicIndicator.TRADE_BALANCE: -0.5 * intensity,  # May worsen initially
                EconomicIndicator.INFLATION: -0.2 * intensity
            }
            sector_impacts = {
                EconomicSector.MANUFACTURING: -1 * intensity,  # May face competition
                EconomicSector.AGRICULTURE: 1.5 * intensity,    # Export opportunities
                EconomicSector.FINANCE: 1 * intensity
            }
            time_to_effect = 12
            effectiveness_score = 0.6
            
        elif policy == PolicyType.TRADE_PROTECTION:
            indicator_impacts = {
                EconomicIndicator.GDP: -0.3 * intensity,
                EconomicIndicator.INFLATION: 0.4 * intensity,
                EconomicIndicator.TRADE_BALANCE: 0.8 * intensity
            }
            sector_impacts = {
                EconomicSector.MANUFACTURING: 1.5 * intensity,
                EconomicSector.AGRICULTURE: -0.5 * intensity,
                EconomicSector.RETAIL: -1 * intensity  # Higher costs
            }
            effectiveness_score = 0.5
            
        return PolicyImpact(
            policy_type=policy,
            indicator_impacts=indicator_impacts,
            sector_impacts=sector_impacts,
            time_to_effect=time_to_effect,
            duration_months=duration_months,
            fiscal_cost=fiscal_cost,
            effectiveness_score=effectiveness_score
        )
    
    def _apply_economic_relationships(self, values: Dict[EconomicIndicator, float]) -> Dict[EconomicIndicator, float]:
        """Apply economic relationships between indicators"""
        new_values = values.copy()
        
        # Phillips Curve: Unemployment vs Inflation
        if EconomicIndicator.UNEMPLOYMENT in values and EconomicIndicator.INFLATION in values:
            unemployment_gap = values[EconomicIndicator.UNEMPLOYMENT] - self.natural_unemployment
            inflation_pressure = -unemployment_gap * self.elasticities['unemployment_inflation'] * 0.1
            new_values[EconomicIndicator.INFLATION] += inflation_pressure
        
        # Interest rate impact on GDP
        if EconomicIndicator.INTEREST_RATE in values and EconomicIndicator.GDP in values:
            real_rate = values[EconomicIndicator.INTEREST_RATE] - values.get(EconomicIndicator.INFLATION, 2.0)
            gdp_adjustment = -real_rate * self.elasticities['gdp_interest'] * 0.01
            new_values[EconomicIndicator.GDP] *= (1 + gdp_adjustment)
        
        # Consumer confidence impact on retail sales
        if EconomicIndicator.CONSUMER_CONFIDENCE in values and EconomicIndicator.RETAIL_SALES in values:
            confidence_effect = (values[EconomicIndicator.CONSUMER_CONFIDENCE] - 100) * 0.05
            new_values[EconomicIndicator.RETAIL_SALES] *= (1 + confidence_effect / 100)
        
        # GDP impact on unemployment (Okun's Law)
        if EconomicIndicator.GDP in values and EconomicIndicator.UNEMPLOYMENT in values:
            gdp_growth = (values[EconomicIndicator.GDP] / 100) - 1  # Convert to growth rate
            unemployment_change = -(gdp_growth - self.trend_growth / 100) * 2  # Okun's coefficient
            new_values[EconomicIndicator.UNEMPLOYMENT] += unemployment_change
            new_values[EconomicIndicator.UNEMPLOYMENT] = max(1.0, new_values[EconomicIndicator.UNEMPLOYMENT])
        
        return new_values


class SectorModel:
    """Sector-specific economic modeling"""
    
    def __init__(self):
        self.sector_multipliers = self._initialize_sector_multipliers()
        self.sector_sensitivities = self._initialize_sector_sensitivities()
        
    def _initialize_sector_multipliers(self) -> Dict[EconomicSector, float]:
        """Initialize sector economic multipliers"""
        return {
            EconomicSector.AGRICULTURE: 0.8,
            EconomicSector.MINING: 1.2,
            EconomicSector.MANUFACTURING: 1.5,
            EconomicSector.UTILITIES: 0.9,
            EconomicSector.CONSTRUCTION: 1.3,
            EconomicSector.WHOLESALE: 1.1,
            EconomicSector.RETAIL: 1.0,
            EconomicSector.TRANSPORTATION: 1.2,
            EconomicSector.INFORMATION: 1.8,
            EconomicSector.FINANCE: 1.4,
            EconomicSector.REAL_ESTATE: 1.1,
            EconomicSector.PROFESSIONAL: 1.3,
            EconomicSector.HEALTHCARE: 0.7,
            EconomicSector.EDUCATION: 0.6,
            EconomicSector.ACCOMMODATION: 1.6,
            EconomicSector.PUBLIC_ADMIN: 0.5
        }
    
    def _initialize_sector_sensitivities(self) -> Dict[EconomicSector, Dict[EconomicShock, float]]:
        """Initialize sector sensitivity to shocks"""
        return {
            EconomicSector.AGRICULTURE: {
                EconomicShock.NATURAL_DISASTER: 2.0,
                EconomicShock.ENERGY_CRISIS: 1.2,
                EconomicShock.SUPPLY_CHAIN_DISRUPTION: 1.5
            },
            EconomicSector.MANUFACTURING: {
                EconomicShock.SUPPLY_CHAIN_DISRUPTION: 2.5,
                EconomicShock.ENERGY_CRISIS: 1.8,
                EconomicShock.TRADE_LIBERALIZATION: -0.5,
                EconomicShock.TRADE_PROTECTION: 0.8
            },
            EconomicSector.RETAIL: {
                EconomicShock.RECESSION: 1.5,
                EconomicShock.PANDEMIC: 2.0,
                EconomicShock.INFLATION_SPIKE: 1.3
            },
            EconomicSector.FINANCE: {
                EconomicShock.FINANCIAL_CRISIS: 3.0,
                EconomicShock.MARKET_CRASH: 2.5,
                EconomicShock.CURRENCY_CRISIS: 2.0
            },
            EconomicSector.ACCOMMODATION: {
                EconomicShock.PANDEMIC: 3.5,
                EconomicShock.GEOPOLITICAL_CRISIS: 1.8,
                EconomicShock.RECESSION: 2.2
            },
            EconomicSector.TRANSPORTATION: {
                EconomicShock.ENERGY_CRISIS: 2.2,
                EconomicShock.SUPPLY_CHAIN_DISRUPTION: 1.8,
                EconomicShock.PANDEMIC: 2.0
            },
            EconomicSector.CONSTRUCTION: {
                EconomicShock.FINANCIAL_CRISIS: 2.5,
                EconomicShock.RECESSION: 2.0,
                EconomicShock.INTEREST_RATE: 1.8
            }
        }
    
    def analyze_sector_impact(self, shock: EconomicShock, intensity: float, 
                            sector: EconomicSector) -> SectorImpact:
        """Analyze shock impact on specific sector"""
        base_sensitivity = self.sector_sensitivities.get(sector, {}).get(shock, 1.0)
        sector_multiplier = self.sector_multipliers.get(sector, 1.0)
        
        gdp_impact = -intensity * base_sensitivity * sector_multiplier
        employment_impact = gdp_impact * 1.2  # Employment more sensitive
        productivity_impact = gdp_impact * 0.5
        investment_impact = gdp_impact * 1.8
        
        # Recovery time varies by sector
        recovery_base = {
            EconomicSector.INFORMATION: 3,
            EconomicSector.FINANCE: 6,
            EconomicSector.MANUFACTURING: 9,
            EconomicSector.RETAIL: 6,
            EconomicSector.CONSTRUCTION: 12,
            EconomicSector.AGRICULTURE: 18,
            EconomicSector.ACCOMMODATION: 15
        }
        
        recovery_months = int(recovery_base.get(sector, 9) * intensity)
        confidence_level = max(0.3, 1.0 - intensity * 0.3)
        
        return SectorImpact(
            sector=sector,
            gdp_impact=gdp_impact,
            employment_impact=employment_impact,
            productivity_impact=productivity_impact,
            investment_impact=investment_impact,
            recovery_months=recovery_months,
            confidence_level=confidence_level
        )
    
    def analyze_all_sectors(self, shock: EconomicShock, intensity: float) -> List[SectorImpact]:
        """Analyze shock impact across all sectors"""
        return [
            self.analyze_sector_impact(shock, intensity, sector)
            for sector in EconomicSector
        ]


class EconomicScenarioPlanner:
    """Main economic scenario planning engine"""
    
    def __init__(self, region: str = "national"):
        self.region = region
        self.macro_model = MacroeconomicModel(region)
        self.sector_model = SectorModel()
        self.scenarios = []
        self.simulation_results = {}
        self.monte_carlo_runs = 1000
        self.confidence_intervals = [0.05, 0.25, 0.75, 0.95]
        
    def create_scenario(self, name: str, description: str, duration_months: int,
                       initial_conditions: Dict[EconomicIndicator, float],
                       shocks: List[Tuple[EconomicShock, int, float]] = None,
                       policies: List[Tuple[PolicyType, int, float]] = None,
                       probability: float = 1.0) -> EconomicScenario:
        """Create a new economic scenario"""
        scenario = EconomicScenario(
            name=name,
            description=description,
            duration_months=duration_months,
            initial_conditions=initial_conditions,
            shocks=shocks or [],
            policies=policies or [],
            probability=probability
        )
        self.scenarios.append(scenario)
        return scenario
    
    def create_baseline_scenario(self, duration_months: int = 60) -> EconomicScenario:
        """Create baseline economic scenario"""
        baseline_conditions = {
            EconomicIndicator.GDP: 100.0,  # Index base
            EconomicIndicator.INFLATION: 2.0,  # Percent
            EconomicIndicator.UNEMPLOYMENT: 5.0,  # Percent
            EconomicIndicator.INTEREST_RATE: 3.0,  # Percent
            EconomicIndicator.CONSUMER_CONFIDENCE: 100.0,  # Index
            EconomicIndicator.BUSINESS_CONFIDENCE: 100.0,  # Index
            EconomicIndicator.STOCK_INDEX: 1000.0,  # Index
            EconomicIndicator.GOVERNMENT_DEBT: 80.0,  # Percent of GDP
            EconomicIndicator.TRADE_BALANCE: -2.0  # Percent of GDP
        }
        
        return self.create_scenario(
            name="Baseline",
            description="Normal economic conditions with trend growth",
            duration_months=duration_months,
            initial_conditions=baseline_conditions,
            probability=0.4
        )
    
    def create_recession_scenario(self, duration_months: int = 24,
                                recession_start: int = 6) -> EconomicScenario:
        """Create recession scenario"""
        baseline_conditions = {
            EconomicIndicator.GDP: 100.0,
            EconomicIndicator.INFLATION: 2.5,
            EconomicIndicator.UNEMPLOYMENT: 4.5,
            EconomicIndicator.INTEREST_RATE: 4.0,
            EconomicIndicator.CONSUMER_CONFIDENCE: 95.0,
            EconomicIndicator.BUSINESS_CONFIDENCE: 98.0,
            EconomicIndicator.STOCK_INDEX: 1050.0
        }
        
        shocks = [(EconomicShock.RECESSION, recession_start, 1.0)]
        policies = [
            (PolicyType.FISCAL_EXPANSION, recession_start + 2, 0.8),
            (PolicyType.MONETARY_EXPANSION, recession_start + 1, 1.0)
        ]
        
        return self.create_scenario(
            name="Recession",
            description="Economic recession with policy response",
            duration_months=duration_months,
            initial_conditions=baseline_conditions,
            shocks=shocks,
            policies=policies,
            probability=0.25
        )
    
    def create_pandemic_scenario(self, duration_months: int = 36) -> EconomicScenario:
        """Create pandemic economic scenario"""
        baseline_conditions = {
            EconomicIndicator.GDP: 100.0,
            EconomicIndicator.INFLATION: 1.8,
            EconomicIndicator.UNEMPLOYMENT: 4.8,
            EconomicIndicator.INTEREST_RATE: 2.5,
            EconomicIndicator.CONSUMER_CONFIDENCE: 105.0,
            EconomicIndicator.BUSINESS_CONFIDENCE: 102.0
        }
        
        shocks = [
            (EconomicShock.PANDEMIC, 3, 1.5),
            (EconomicShock.SUPPLY_CHAIN_DISRUPTION, 6, 1.0),
            (EconomicShock.INFLATION_SPIKE, 18, 0.8)
        ]
        
        policies = [
            (PolicyType.FISCAL_EXPANSION, 3, 2.0),
            (PolicyType.MONETARY_EXPANSION, 2, 1.5),
            (PolicyType.SPENDING_INCREASE, 4, 1.2)
        ]
        
        return self.create_scenario(
            name="Pandemic",
            description="Pandemic-induced economic disruption",
            duration_months=duration_months,
            initial_conditions=baseline_conditions,
            shocks=shocks,
            policies=policies,
            probability=0.15
        )
    
    def create_inflation_scenario(self, duration_months: int = 30) -> EconomicScenario:
        """Create high inflation scenario"""
        baseline_conditions = {
            EconomicIndicator.GDP: 100.0,
            EconomicIndicator.INFLATION: 2.2,
            EconomicIndicator.UNEMPLOYMENT: 4.2,
            EconomicIndicator.INTEREST_RATE: 3.5,
            EconomicIndicator.CONSUMER_CONFIDENCE: 98.0,
            EconomicIndicator.BUSINESS_CONFIDENCE: 100.0
        }
        
        shocks = [
            (EconomicShock.ENERGY_CRISIS, 2, 1.2),
            (EconomicShock.SUPPLY_CHAIN_DISRUPTION, 4, 0.8),
            (EconomicShock.INFLATION_SPIKE, 6, 1.5)
        ]
        
        policies = [
            (PolicyType.MONETARY_CONTRACTION, 8, 1.0),
            (PolicyType.FISCAL_CONTRACTION, 12, 0.6)
        ]
        
        return self.create_scenario(
            name="High Inflation",
            description="Persistent inflation requiring monetary tightening",
            duration_months=duration_months,
            initial_conditions=baseline_conditions,
            shocks=shocks,
            policies=policies,
            probability=0.2
        )
    
    def simulate_scenario(self, scenario: EconomicScenario) -> Dict[EconomicIndicator, List[float]]:
        """Simulate a single scenario"""
        return self.macro_model.simulate(scenario.duration_months, scenario)
    
    def run_monte_carlo(self, scenario: EconomicScenario, runs: int = None) -> Dict[str, Any]:
        """Run Monte Carlo simulation for scenario"""
        runs = runs or self.monte_carlo_runs
        all_results = defaultdict(list)
        
        for run in range(runs):
            # Add randomness to scenario parameters
            random_scenario = self._randomize_scenario(scenario)
            results = self.simulate_scenario(random_scenario)
            
            # Store final values for each indicator
            for indicator, values in results.items():
                if values:
                    all_results[indicator.value].append(values[-1])
        
        # Calculate statistics
        statistics = {}
        for indicator, values in all_results.items():
            values_array = np.array(values)
            statistics[indicator] = {
                'mean': float(np.mean(values_array)),
                'std': float(np.std(values_array)),
                'min': float(np.min(values_array)),
                'max': float(np.max(values_array)),
                'percentiles': {
                    f'p{int(p*100)}': float(np.percentile(values_array, p*100))
                    for p in self.confidence_intervals
                }
            }
        
        return {
            'runs': runs,
            'statistics': statistics,
            'scenario': scenario.name,
            'duration_months': scenario.duration_months
        }
    
    def compare_scenarios(self, scenarios: List[EconomicScenario] = None) -> Dict[str, Any]:
        """Compare multiple scenarios"""
        if scenarios is None:
            scenarios = self.scenarios
        
        comparison = {
            'scenarios': [],
            'indicators': defaultdict(dict),
            'risks': {},
            'opportunities': {}
        }
        
        for scenario in scenarios:
            results = self.simulate_scenario(scenario)
            scenario_summary = {
                'name': scenario.name,
                'probability': scenario.probability,
                'final_values': {}
            }
            
            for indicator, values in results.items():
                if values:
                    final_value = values[-1]
                    scenario_summary['final_values'][indicator.value] = final_value
                    comparison['indicators'][indicator.value][scenario.name] = final_value
            
            comparison['scenarios'].append(scenario_summary)
        
        # Identify risks and opportunities
        for indicator, scenario_values in comparison['indicators'].items():
            values = list(scenario_values.values())
            comparison['risks'][indicator] = {
                'worst_case': min(values),
                'worst_scenario': min(scenario_values.keys(), key=lambda k: scenario_values[k])
            }
            comparison['opportunities'][indicator] = {
                'best_case': max(values),
                'best_scenario': max(scenario_values.keys(), key=lambda k: scenario_values[k])
            }
        
        return comparison
    
    def analyze_policy_effectiveness(self, base_scenario: EconomicScenario,
                                   policy_alternatives: List[Tuple[PolicyType, float]]) -> Dict[str, Any]:
        """Analyze effectiveness of different policy alternatives"""
        base_results = self.simulate_scenario(base_scenario)
        policy_analysis = {'base_scenario': base_scenario.name, 'alternatives': []}
        
        for policy_type, intensity in policy_alternatives:
            # Create modified scenario with policy
            policy_scenario = EconomicScenario(
                name=f"{base_scenario.name}_with_{policy_type.value}",
                description=f"{base_scenario.description} with {policy_type.value}",
                duration_months=base_scenario.duration_months,
                initial_conditions=base_scenario.initial_conditions.copy(),
                shocks=base_scenario.shocks.copy(),
                policies=base_scenario.policies + [(policy_type, 1, intensity)],
                probability=base_scenario.probability
            )
            
            policy_results = self.simulate_scenario(policy_scenario)
            policy_impact = self.macro_model.evaluate_policy(policy_type, intensity)
            
            # Calculate improvement
            improvements = {}
            for indicator in base_results.keys():
                if indicator in policy_results:
                    base_final = base_results[indicator][-1] if base_results[indicator] else 0
                    policy_final = policy_results[indicator][-1] if policy_results[indicator] else 0
                    improvements[indicator.value] = policy_final - base_final
            
            policy_analysis['alternatives'].append({
                'policy': policy_type.value,
                'intensity': intensity,
                'fiscal_cost': policy_impact.fiscal_cost,
                'effectiveness_score': policy_impact.effectiveness_score,
                'improvements': improvements,
                'cost_effectiveness': policy_impact.effectiveness_score / max(abs(policy_impact.fiscal_cost), 1)
            })
        
        # Rank policies by cost-effectiveness
        policy_analysis['alternatives'].sort(key=lambda x: x['cost_effectiveness'], reverse=True)
        
        return policy_analysis
    
    def generate_stress_test(self, base_scenario: EconomicScenario,
                           stress_factors: List[Tuple[EconomicShock, float]]) -> Dict[str, Any]:
        """Generate stress test scenarios"""
        stress_results = {'base_scenario': base_scenario.name, 'stress_tests': []}
        
        for shock_type, intensity in stress_factors:
            stress_scenario = EconomicScenario(
                name=f"{base_scenario.name}_stress_{shock_type.value}",
                description=f"Stress test: {shock_type.value} at {intensity} intensity",
                duration_months=base_scenario.duration_months,
                initial_conditions=base_scenario.initial_conditions.copy(),
                shocks=base_scenario.shocks + [(shock_type, 1, intensity)],
                policies=base_scenario.policies.copy(),
                probability=0.05
            )
            
            stress_test_results = self.simulate_scenario(stress_scenario)
            
            # Analyze sector impacts
            sector_impacts = self.sector_model.analyze_all_sectors(shock_type, intensity)
            
            stress_results['stress_tests'].append({
                'shock_type': shock_type.value,
                'intensity': intensity,
                'economic_results': {
                    indicator.value: values[-1] if values else 0
                    for indicator, values in stress_test_results.items()
                },
                'sector_impacts': [
                    {
                        'sector': impact.sector.value,
                        'gdp_impact': impact.gdp_impact,
                        'employment_impact': impact.employment_impact,
                        'recovery_months': impact.recovery_months
                    }
                    for impact in sector_impacts
                ]
            })
        
        return stress_results
    
    def optimize_policy_mix(self, target_scenario: EconomicScenario,
                          available_policies: List[PolicyType],
                          target_indicators: Dict[EconomicIndicator, float]) -> Dict[str, Any]:
        """Optimize policy mix to achieve target indicators"""
        best_score = float('-inf')
        best_mix = []
        optimization_results = []
        
        # Simple grid search for policy optimization
        intensity_levels = [0.2, 0.5, 0.8, 1.0, 1.2]
        
        for num_policies in range(1, min(4, len(available_policies) + 1)):
            from itertools import combinations, product
            
            for policy_combo in combinations(available_policies, num_policies):
                for intensities in product(intensity_levels, repeat=num_policies):
                    policies = list(zip(policy_combo, [1] * num_policies, intensities))
                    
                    test_scenario = EconomicScenario(
                        name=f"optimization_test",
                        description="Policy optimization test",
                        duration_months=target_scenario.duration_months,
                        initial_conditions=target_scenario.initial_conditions.copy(),
                        shocks=target_scenario.shocks.copy(),
                        policies=policies,
                        probability=1.0
                    )
                    
                    results = self.simulate_scenario(test_scenario)
                    score = self._calculate_policy_score(results, target_indicators)
                    
                    optimization_results.append({
                        'policies': [(p.value, i) for p, _, i in policies],
                        'score': score,
                        'final_values': {
                            indicator.value: values[-1] if values else 0
                            for indicator, values in results.items()
                        }
                    })
                    
                    if score > best_score:
                        best_score = score
                        best_mix = policies
        
        return {
            'best_policy_mix': [(p.value, i) for p, _, i in best_mix],
            'best_score': best_score,
            'all_results': sorted(optimization_results, key=lambda x: x['score'], reverse=True)[:10]
        }
    
    def export_scenario_data(self, scenario_name: str = None) -> Dict[str, Any]:
        """Export scenario data for analysis"""
        if scenario_name:
            scenarios = [s for s in self.scenarios if s.name == scenario_name]
        else:
            scenarios = self.scenarios
        
        export_data = {
            'region': self.region,
            'scenarios': [],
            'model_parameters': {
                'multipliers': self.macro_model.multipliers,
                'elasticities': self.macro_model.elasticities,
                'trend_growth': self.macro_model.trend_growth,
                'natural_unemployment': self.macro_model.natural_unemployment
            },
            'export_timestamp': datetime.now().isoformat()
        }
        
        for scenario in scenarios:
            scenario_data = {
                'name': scenario.name,
                'description': scenario.description,
                'duration_months': scenario.duration_months,
                'initial_conditions': {k.value: v for k, v in scenario.initial_conditions.items()},
                'shocks': [(s.value, m, i) for s, m, i in scenario.shocks],
                'policies': [(p.value, m, i) for p, m, i in scenario.policies],
                'probability': scenario.probability,
                'created_at': scenario.created_at.isoformat()
            }
            
            # Add simulation results if available
            if scenario.name in self.simulation_results:
                scenario_data['results'] = self.simulation_results[scenario.name]
            
            export_data['scenarios'].append(scenario_data)
        
        return export_data
    
    def _randomize_scenario(self, scenario: EconomicScenario) -> EconomicScenario:
        """Add randomness to scenario for Monte Carlo"""
        # Add noise to initial conditions
        random_conditions = {}
        for indicator, value in scenario.initial_conditions.items():
            noise = random.gauss(0, 0.05)  # 5% standard deviation
            random_conditions[indicator] = value * (1 + noise)
        
        # Add randomness to shock timing and intensity
        random_shocks = []
        for shock_type, month, intensity in scenario.shocks:
            random_month = max(0, month + random.randint(-1, 2))
            random_intensity = intensity * random.uniform(0.8, 1.2)
            random_shocks.append((shock_type, random_month, random_intensity))
        
        return EconomicScenario(
            name=f"{scenario.name}_random",
            description=scenario.description,
            duration_months=scenario.duration_months,
            initial_conditions=random_conditions,
            shocks=random_shocks,
            policies=scenario.policies,
            probability=scenario.probability
        )
    
    def _calculate_policy_score(self, results: Dict[EconomicIndicator, List[float]],
                              targets: Dict[EconomicIndicator, float]) -> float:
        """Calculate policy effectiveness score"""
        score = 0
        for indicator, target in targets.items():
            if indicator in results and results[indicator]:
                actual = results[indicator][-1]
                # Score based on how close we get to target (higher is better for most indicators)
                if indicator in [EconomicIndicator.UNEMPLOYMENT, EconomicIndicator.INFLATION]:
                    # Lower is better for these indicators
                    score += max(0, 100 - abs(actual - target) * 10)
                else:
                    # Higher is better for GDP, confidence, etc.
                    score += max(0, 100 - abs((actual - target) / target) * 100)
        
        return score / len(targets) if targets else 0


# Example usage and testing
if __name__ == "__main__":
    async def main():
        # Create economic scenario planner
        planner = EconomicScenarioPlanner("United States")
        
        # Create baseline scenarios
        baseline = planner.create_baseline_scenario(60)
        recession = planner.create_recession_scenario(36)
        pandemic = planner.create_pandemic_scenario(48)
        inflation = planner.create_inflation_scenario(24)
        
        print(f"Created {len(planner.scenarios)} scenarios")
        
        # Simulate baseline scenario
        baseline_results = planner.simulate_scenario(baseline)
        print(f"Baseline GDP final value: {baseline_results[EconomicIndicator.GDP][-1]:.2f}")
        print(f"Baseline unemployment final: {baseline_results[EconomicIndicator.UNEMPLOYMENT][-1]:.2f}%")
        
        # Run Monte Carlo simulation
        mc_results = planner.run_monte_carlo(recession, 500)
        gdp_stats = mc_results['statistics']['gdp']
        print(f"Recession scenario GDP: mean={gdp_stats['mean']:.2f}, std={gdp_stats['std']:.2f}")
        
        # Compare scenarios
        comparison = planner.compare_scenarios()
        print(f"GDP worst case: {comparison['risks']['gdp']['worst_case']:.2f} in {comparison['risks']['gdp']['worst_scenario']}")
        
        # Analyze policy effectiveness
        policy_analysis = planner.analyze_policy_effectiveness(
            recession,
            [(PolicyType.FISCAL_EXPANSION, 1.0), (PolicyType.MONETARY_EXPANSION, 0.8)]
        )
        print(f"Best policy: {policy_analysis['alternatives'][0]['policy']} with cost-effectiveness {policy_analysis['alternatives'][0]['cost_effectiveness']:.3f}")
        
        # Stress testing
        stress_tests = planner.generate_stress_test(
            baseline,
            [(EconomicShock.FINANCIAL_CRISIS, 1.5), (EconomicShock.PANDEMIC, 2.0)]
        )
        print(f"Generated {len(stress_tests['stress_tests'])} stress test scenarios")
        
        # Policy optimization
        targets = {
            EconomicIndicator.GDP: 102.0,
            EconomicIndicator.UNEMPLOYMENT: 4.0,
            EconomicIndicator.INFLATION: 2.0
        }
        optimization = planner.optimize_policy_mix(
            recession,
            [PolicyType.FISCAL_EXPANSION, PolicyType.MONETARY_EXPANSION, PolicyType.TAX_CUT],
            targets
        )
        print(f"Optimal policy mix score: {optimization['best_score']:.2f}")
        print(f"Best policies: {optimization['best_policy_mix']}")
        
        # Export results
        export_data = planner.export_scenario_data()
        print(f"Exported data for {len(export_data['scenarios'])} scenarios")
    
    # Run the example
    asyncio.run(main())