#!/usr/bin/env python3
"""
Pricing Strategy Optimizer for ActiveLog Economic Simulator
Advanced optimization of pricing strategies using multi-objective optimization
"""

import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)


class PricingModel(Enum):
    """Types of pricing models"""
    FREEMIUM = "freemium"
    SUBSCRIPTION = "subscription"
    PAY_PER_USE = "pay_per_use"
    TIERED = "tiered" 
    ENTERPRISE = "enterprise"
    USAGE_BASED = "usage_based"
    HYBRID = "hybrid"


class OptimizationGoal(Enum):
    """Optimization objectives"""
    REVENUE_MAXIMIZATION = "revenue_maximization"
    USER_ACQUISITION = "user_acquisition"
    MARKET_PENETRATION = "market_penetration"
    PROFIT_MAXIMIZATION = "profit_maximization"
    COMPETITIVE_POSITIONING = "competitive_positioning"
    CUSTOMER_LIFETIME_VALUE = "customer_lifetime_value"


@dataclass
class PricingScenario:
    """Pricing strategy scenario"""
    scenario_id: str
    pricing_model: PricingModel
    price_points: Dict[str, float]
    features_included: Dict[str, List[str]]
    target_segments: List[str]
    expected_conversion_rates: Dict[str, float]
    estimated_costs: Dict[str, float]


class PricingStrategyOptimizer:
    """Advanced pricing strategy optimization and testing system"""
    
    def __init__(self, config):
        self.config = config
        self.pricing_models = {}
        self.market_data = {}
        self.optimization_results = {}
        
        # Initialize pricing model templates
        self._initialize_pricing_models()
        
        # Initialize market elasticity data
        self._initialize_market_elasticity()
        
        logger.info("PricingStrategyOptimizer initialized")
    
    def optimize_pricing(self, pricing_scenarios: List[Dict[str, Any]], 
                        optimization_goals: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize pricing strategies across multiple scenarios"""
        try:
            # Parse scenarios and goals
            parsed_scenarios = self._parse_pricing_scenarios(pricing_scenarios)
            parsed_goals = self._parse_optimization_goals(optimization_goals)
            
            # Run optimization for each scenario
            scenario_results = []
            for scenario in parsed_scenarios:
                result = self._optimize_single_scenario(scenario, parsed_goals)
                scenario_results.append(result)
            
            # Compare scenarios and rank them
            scenario_ranking = self._rank_scenarios(scenario_results, parsed_goals)
            
            # Generate optimization insights
            optimization_insights = self._generate_optimization_insights(
                scenario_results, scenario_ranking
            )
            
            # Create implementation recommendations
            implementation_plan = self._create_implementation_plan(
                scenario_ranking, optimization_insights
            )
            
            return {
                'optimization_id': f"pricing_opt_{int(datetime.utcnow().timestamp())}",
                'scenario_results': scenario_results,
                'scenario_ranking': scenario_ranking,
                'recommended_strategy': scenario_ranking[0] if scenario_ranking else None,
                'optimization_insights': optimization_insights,
                'implementation_plan': implementation_plan,
                'sensitivity_analysis': self._perform_sensitivity_analysis(scenario_ranking[0] if scenario_ranking else None),
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to optimize pricing strategy: {e}")
            return {'error': str(e)}
    
    def _initialize_pricing_models(self):
        """Initialize pricing model templates and configurations"""
        
        self.pricing_models = {
            PricingModel.FREEMIUM: {
                'tiers': {
                    'free': {
                        'price': 0.0,
                        'features': ['basic_logging', 'limited_search', 'basic_export'],
                        'limits': {'entries_per_month': 100, 'storage_mb': 50}
                    },
                    'pro': {
                        'price': 9.99,
                        'features': ['unlimited_logging', 'advanced_search', 'full_export', 'integrations'],
                        'limits': {'entries_per_month': -1, 'storage_gb': 10}
                    },
                    'team': {
                        'price': 29.99,
                        'features': ['all_pro_features', 'team_collaboration', 'admin_controls'],
                        'limits': {'team_members': 10, 'storage_gb': 100}
                    }
                },
                'conversion_rates': {'free_to_pro': 0.05, 'pro_to_team': 0.15},
                'typical_ltv_multiplier': 1.2
            },
            
            PricingModel.SUBSCRIPTION: {
                'tiers': {
                    'basic': {
                        'price': 5.99,
                        'features': ['core_functionality', 'basic_support'],
                        'limits': {'users': 1}
                    },
                    'standard': {
                        'price': 14.99,
                        'features': ['all_basic', 'advanced_features', 'priority_support'],
                        'limits': {'users': 5}
                    },
                    'premium': {
                        'price': 24.99,
                        'features': ['all_standard', 'premium_features', 'custom_integrations'],
                        'limits': {'users': -1}
                    }
                },
                'conversion_rates': {'trial_to_basic': 0.25, 'basic_to_standard': 0.20, 'standard_to_premium': 0.10},
                'typical_ltv_multiplier': 1.8
            },
            
            PricingModel.PAY_PER_USE: {
                'pricing_units': {
                    'api_calls': {'price_per_1000': 2.00, 'volume_discounts': {10000: 0.15, 100000: 0.25}},
                    'storage_gb': {'price_per_gb_month': 0.50},
                    'compute_hours': {'price_per_hour': 0.10, 'instance_type_multipliers': {'basic': 1.0, 'performance': 2.0}}
                },
                'typical_ltv_multiplier': 0.8
            },
            
            PricingModel.ENTERPRISE: {
                'base_price': 500.0,
                'per_user_price': 25.0,
                'volume_discounts': {50: 0.10, 100: 0.20, 500: 0.30},
                'custom_features_price': 1000.0,
                'typical_ltv_multiplier': 3.0
            }
        }
    
    def _initialize_market_elasticity(self):
        """Initialize market elasticity data for different segments"""
        
        self.market_data = {
            'price_elasticity_by_segment': {
                'individual_developers': -1.2,  # Highly price sensitive
                'small_teams': -0.8,           # Moderately price sensitive
                'medium_businesses': -0.5,     # Less price sensitive
                'enterprise': -0.2,            # Least price sensitive
                'students': -2.0,              # Extremely price sensitive
                'non_profits': -1.5            # Very price sensitive
            },
            'competitive_landscape': {
                'direct_competitors': {
                    'notion': {'pricing': [0, 8, 16], 'market_share': 0.25},
                    'obsidian': {'pricing': [0, 50], 'market_share': 0.15},
                    'roam': {'pricing': [15], 'market_share': 0.10}
                },
                'indirect_competitors': {
                    'google_docs': {'pricing': [0], 'market_share': 0.40},
                    'microsoft_onenote': {'pricing': [0, 6.99], 'market_share': 0.30}
                }
            },
            'market_size_estimates': {
                'total_addressable_market': 50000000,
                'serviceable_addressable_market': 10000000,
                'serviceable_obtainable_market': 500000
            }
        }
    
    def _parse_pricing_scenarios(self, pricing_scenarios: List[Dict[str, Any]]) -> List[PricingScenario]:
        """Parse and validate pricing scenarios"""
        
        parsed_scenarios = []
        
        for i, scenario_data in enumerate(pricing_scenarios):
            scenario = PricingScenario(
                scenario_id=scenario_data.get('scenario_id', f'scenario_{i}'),
                pricing_model=PricingModel(scenario_data.get('pricing_model', 'freemium')),
                price_points=scenario_data.get('price_points', {}),
                features_included=scenario_data.get('features_included', {}),
                target_segments=scenario_data.get('target_segments', ['individual_developers']),
                expected_conversion_rates=scenario_data.get('expected_conversion_rates', {}),
                estimated_costs=scenario_data.get('estimated_costs', {})
            )
            parsed_scenarios.append(scenario)
        
        return parsed_scenarios
    
    def _parse_optimization_goals(self, optimization_goals: Dict[str, Any]) -> Dict[OptimizationGoal, float]:
        """Parse optimization goals with weights"""
        
        parsed_goals = {}
        total_weight = 0
        
        for goal_name, weight in optimization_goals.items():
            try:
                goal_enum = OptimizationGoal(goal_name)
                parsed_goals[goal_enum] = float(weight)
                total_weight += float(weight)
            except (ValueError, TypeError):
                logger.warning(f"Invalid optimization goal: {goal_name}")
        
        # Normalize weights to sum to 1.0
        if total_weight > 0:
            for goal in parsed_goals:
                parsed_goals[goal] = parsed_goals[goal] / total_weight
        
        return parsed_goals
    
    def _optimize_single_scenario(self, scenario: PricingScenario, 
                                 optimization_goals: Dict[OptimizationGoal, float]) -> Dict[str, Any]:
        """Optimize a single pricing scenario"""
        
        # Calculate key metrics for this scenario
        revenue_projection = self._calculate_revenue_projection(scenario)
        user_acquisition_projection = self._calculate_user_acquisition(scenario)
        market_penetration = self._calculate_market_penetration(scenario)
        profit_projection = self._calculate_profit_projection(scenario)
        competitive_position = self._assess_competitive_position(scenario)
        ltv_projection = self._calculate_ltv_projection(scenario)
        
        # Calculate weighted optimization score
        metrics = {
            OptimizationGoal.REVENUE_MAXIMIZATION: revenue_projection.get('score', 0),
            OptimizationGoal.USER_ACQUISITION: user_acquisition_projection.get('score', 0),
            OptimizationGoal.MARKET_PENETRATION: market_penetration.get('score', 0),
            OptimizationGoal.PROFIT_MAXIMIZATION: profit_projection.get('score', 0),
            OptimizationGoal.COMPETITIVE_POSITIONING: competitive_position.get('score', 0),
            OptimizationGoal.CUSTOMER_LIFETIME_VALUE: ltv_projection.get('score', 0)
        }
        
        weighted_score = sum(
            metrics.get(goal, 0) * weight
            for goal, weight in optimization_goals.items()
        )
        
        return {
            'scenario_id': scenario.scenario_id,
            'pricing_model': scenario.pricing_model.value,
            'weighted_optimization_score': weighted_score,
            'individual_scores': {goal.value: score for goal, score in metrics.items()},
            'projections': {
                'revenue': revenue_projection,
                'user_acquisition': user_acquisition_projection,
                'market_penetration': market_penetration,
                'profit': profit_projection,
                'competitive_position': competitive_position,
                'customer_ltv': ltv_projection
            },
            'risk_assessment': self._assess_pricing_risks(scenario),
            'implementation_complexity': self._assess_implementation_complexity(scenario)
        }
    
    def _calculate_revenue_projection(self, scenario: PricingScenario) -> Dict[str, Any]:
        """Calculate revenue projection for pricing scenario"""
        
        model_template = self.pricing_models.get(scenario.pricing_model)
        if not model_template:
            return {'monthly_revenue': 0, 'annual_revenue': 0, 'score': 0}
        
        monthly_revenue = 0
        user_segments = {
            'individual_developers': 1000,
            'small_teams': 300,
            'medium_businesses': 100,
            'enterprise': 20
        }
        
        for segment, user_count in user_segments.items():
            if segment in scenario.target_segments:
                # Apply price elasticity
                elasticity = self.market_data['price_elasticity_by_segment'].get(segment, -1.0)
                
                if scenario.pricing_model == PricingModel.FREEMIUM:
                    # Calculate freemium conversion revenue
                    free_users = user_count
                    pro_conversion_rate = model_template['conversion_rates'].get('free_to_pro', 0.05)
                    pro_users = free_users * pro_conversion_rate
                    pro_price = model_template['tiers']['pro']['price']
                    
                    segment_revenue = pro_users * pro_price
                    
                elif scenario.pricing_model == PricingModel.SUBSCRIPTION:
                    # Calculate subscription revenue with tier distribution
                    avg_price = np.mean([tier['price'] for tier in model_template['tiers'].values()])
                    segment_revenue = user_count * avg_price * 0.6  # 60% conversion rate
                    
                elif scenario.pricing_model == PricingModel.PAY_PER_USE:
                    # Calculate usage-based revenue
                    avg_monthly_usage = user_count * 50  # Assume $50 average monthly usage
                    segment_revenue = avg_monthly_usage
                    
                else:
                    # Default calculation
                    avg_price = np.mean(list(scenario.price_points.values())) if scenario.price_points else 15.0
                    segment_revenue = user_count * avg_price * 0.5  # 50% conversion rate
                
                monthly_revenue += segment_revenue
        
        annual_revenue = monthly_revenue * 12
        
        # Score based on revenue potential (normalize to 0-100)
        max_potential_revenue = 1000000  # $1M monthly
        score = min(100, (monthly_revenue / max_potential_revenue) * 100)
        
        return {
            'monthly_revenue': monthly_revenue,
            'annual_revenue': annual_revenue,
            'revenue_per_user': monthly_revenue / max(1, sum(user_segments.values())),
            'score': score,
            'growth_projection': annual_revenue * 1.5  # Assume 50% annual growth
        }
    
    def _calculate_user_acquisition(self, scenario: PricingScenario) -> Dict[str, Any]:
        """Calculate user acquisition metrics"""
        
        base_acquisition_rate = 1000  # Users per month
        
        # Adjust based on pricing model
        if scenario.pricing_model == PricingModel.FREEMIUM:
            acquisition_multiplier = 2.0  # Free tier drives more users
        elif scenario.pricing_model == PricingModel.PAY_PER_USE:
            acquisition_multiplier = 1.2  # Lower barrier to entry
        else:
            acquisition_multiplier = 1.0
        
        # Adjust based on competitive pricing
        competitive_adjustment = self._get_competitive_pricing_adjustment(scenario)
        
        projected_monthly_acquisition = base_acquisition_rate * acquisition_multiplier * competitive_adjustment
        
        # Score based on acquisition potential
        max_acquisition = 5000  # 5K users per month max
        score = min(100, (projected_monthly_acquisition / max_acquisition) * 100)
        
        return {
            'projected_monthly_acquisition': projected_monthly_acquisition,
            'projected_annual_acquisition': projected_monthly_acquisition * 12,
            'acquisition_cost_estimate': 25.0,  # $25 CAC estimate
            'score': score,
            'conversion_funnel': {
                'awareness': projected_monthly_acquisition * 10,
                'consideration': projected_monthly_acquisition * 3,
                'trial': projected_monthly_acquisition * 1.5,
                'conversion': projected_monthly_acquisition
            }
        }
    
    def _calculate_market_penetration(self, scenario: PricingScenario) -> Dict[str, Any]:
        """Calculate market penetration potential"""
        
        som = self.market_data['market_size_estimates']['serviceable_obtainable_market']
        
        # Base penetration rate based on pricing model
        base_penetration_rates = {
            PricingModel.FREEMIUM: 0.05,     # 5% of SOM
            PricingModel.SUBSCRIPTION: 0.03,  # 3% of SOM
            PricingModel.PAY_PER_USE: 0.02,  # 2% of SOM
            PricingModel.ENTERPRISE: 0.01    # 1% of SOM
        }
        
        base_rate = base_penetration_rates.get(scenario.pricing_model, 0.02)
        
        # Adjust for competitive factors
        competitive_factor = 1.0
        if self._is_pricing_competitive(scenario):
            competitive_factor = 1.2
        elif self._is_pricing_premium(scenario):
            competitive_factor = 0.8
        
        projected_penetration = base_rate * competitive_factor
        projected_users = som * projected_penetration
        
        # Score based on penetration achievement
        target_penetration = 0.05  # 5% target
        score = min(100, (projected_penetration / target_penetration) * 100)
        
        return {
            'projected_penetration_rate': projected_penetration,
            'projected_user_base': projected_users,
            'time_to_penetration_months': 24,  # Estimate 2 years
            'score': score,
            'market_share_potential': projected_penetration * 0.2  # 20% of penetration becomes market share
        }
    
    def _calculate_profit_projection(self, scenario: PricingScenario) -> Dict[str, Any]:
        """Calculate profit projection"""
        
        revenue_projection = self._calculate_revenue_projection(scenario)
        monthly_revenue = revenue_projection['monthly_revenue']
        
        # Estimate costs based on pricing model
        cost_structures = {
            PricingModel.FREEMIUM: 0.4,      # 40% cost ratio (high due to free tier)
            PricingModel.SUBSCRIPTION: 0.3,  # 30% cost ratio
            PricingModel.PAY_PER_USE: 0.5,  # 50% cost ratio (variable costs)
            PricingModel.ENTERPRISE: 0.25   # 25% cost ratio (economies of scale)
        }
        
        cost_ratio = cost_structures.get(scenario.pricing_model, 0.35)
        monthly_costs = monthly_revenue * cost_ratio
        monthly_profit = monthly_revenue - monthly_costs
        
        # Add fixed costs
        fixed_monthly_costs = 10000  # $10K fixed costs
        net_monthly_profit = monthly_profit - fixed_monthly_costs
        
        profit_margin = (net_monthly_profit / monthly_revenue) if monthly_revenue > 0 else 0
        
        # Score based on profit potential
        target_margin = 0.20  # 20% target margin
        score = min(100, max(0, (profit_margin / target_margin) * 100))
        
        return {
            'monthly_profit': net_monthly_profit,
            'annual_profit': net_monthly_profit * 12,
            'profit_margin': profit_margin,
            'break_even_months': max(1, abs(fixed_monthly_costs / max(1, monthly_profit - fixed_monthly_costs))),
            'score': score
        }
    
    def _assess_competitive_position(self, scenario: PricingScenario) -> Dict[str, Any]:
        """Assess competitive positioning"""
        
        competitive_landscape = self.market_data['competitive_landscape']
        
        # Get average competitor prices
        direct_competitor_prices = []
        for competitor, data in competitive_landscape['direct_competitors'].items():
            direct_competitor_prices.extend(data['pricing'])
        
        avg_competitor_price = np.mean([p for p in direct_competitor_prices if p > 0]) if direct_competitor_prices else 15.0
        
        # Calculate our average price
        our_avg_price = np.mean(list(scenario.price_points.values())) if scenario.price_points else 15.0
        
        # Competitive position assessment
        price_ratio = our_avg_price / avg_competitor_price if avg_competitor_price > 0 else 1.0
        
        if price_ratio < 0.8:
            position = 'cost_leader'
            score = 85
        elif price_ratio < 1.2:
            position = 'competitive'
            score = 90
        elif price_ratio < 1.5:
            position = 'premium'
            score = 75
        else:
            position = 'luxury'
            score = 60
        
        return {
            'competitive_position': position,
            'price_ratio_vs_competition': price_ratio,
            'market_position_strength': score,
            'differentiation_opportunities': self._identify_differentiation_opportunities(scenario),
            'score': score
        }
    
    def _calculate_ltv_projection(self, scenario: PricingScenario) -> Dict[str, Any]:
        """Calculate customer lifetime value projection"""
        
        model_template = self.pricing_models.get(scenario.pricing_model)
        ltv_multiplier = model_template.get('typical_ltv_multiplier', 1.0) if model_template else 1.0
        
        # Base calculation
        avg_monthly_revenue_per_user = 25.0  # Estimate
        avg_customer_lifespan_months = 18    # Estimate
        churn_rate = 0.05  # 5% monthly churn
        
        # Adjust based on pricing model
        if scenario.pricing_model == PricingModel.FREEMIUM:
            # Freemium users have different LTV profiles
            free_user_ltv = 0
            paid_user_ltv = avg_monthly_revenue_per_user / churn_rate
            conversion_rate = 0.05
            blended_ltv = (free_user_ltv * (1 - conversion_rate)) + (paid_user_ltv * conversion_rate)
        else:
            blended_ltv = avg_monthly_revenue_per_user / churn_rate
        
        # Apply model-specific multiplier
        final_ltv = blended_ltv * ltv_multiplier
        
        # Calculate LTV/CAC ratio
        estimated_cac = 25.0  # $25 customer acquisition cost
        ltv_cac_ratio = final_ltv / estimated_cac
        
        # Score based on LTV potential
        target_ltv = 500.0  # $500 target LTV
        score = min(100, (final_ltv / target_ltv) * 100)
        
        return {
            'projected_ltv': final_ltv,
            'ltv_cac_ratio': ltv_cac_ratio,
            'payback_period_months': estimated_cac / avg_monthly_revenue_per_user,
            'retention_rate': 1 - churn_rate,
            'score': score
        }
    
    def _get_competitive_pricing_adjustment(self, scenario: PricingScenario) -> float:
        """Get competitive pricing adjustment factor"""
        
        if self._is_pricing_competitive(scenario):
            return 1.2  # 20% boost for competitive pricing
        elif self._is_pricing_premium(scenario):
            return 0.8  # 20% penalty for premium pricing
        else:
            return 1.0  # Neutral
    
    def _is_pricing_competitive(self, scenario: PricingScenario) -> bool:
        """Check if pricing is competitive"""
        # Simplified competitive check
        avg_price = np.mean(list(scenario.price_points.values())) if scenario.price_points else 15.0
        return avg_price <= 20.0  # Under $20 is competitive
    
    def _is_pricing_premium(self, scenario: PricingScenario) -> bool:
        """Check if pricing is premium"""
        avg_price = np.mean(list(scenario.price_points.values())) if scenario.price_points else 15.0
        return avg_price >= 30.0  # Over $30 is premium
    
    def _identify_differentiation_opportunities(self, scenario: PricingScenario) -> List[str]:
        """Identify differentiation opportunities"""
        opportunities = []
        
        if scenario.pricing_model == PricingModel.FREEMIUM:
            opportunities.extend([
                'Enhanced free tier features',
                'Faster upgrade incentives',
                'Community features'
            ])
        
        if 'enterprise' in scenario.target_segments:
            opportunities.extend([
                'Custom integrations',
                'Dedicated support',
                'Advanced security features'
            ])
        
        return opportunities
    
    def _assess_pricing_risks(self, scenario: PricingScenario) -> Dict[str, Any]:
        """Assess risks associated with pricing scenario"""
        
        risks = []
        risk_score = 0
        
        # Price elasticity risk
        for segment in scenario.target_segments:
            elasticity = self.market_data['price_elasticity_by_segment'].get(segment, -1.0)
            if elasticity < -1.5:  # Highly elastic
                risks.append(f"High price sensitivity in {segment} segment")
                risk_score += 20
        
        # Competitive risk
        if self._is_pricing_premium(scenario):
            risks.append("Premium pricing may limit market adoption")
            risk_score += 15
        
        # Model complexity risk
        if scenario.pricing_model in [PricingModel.HYBRID, PricingModel.USAGE_BASED]:
            risks.append("Complex pricing model may confuse customers")
            risk_score += 10
        
        return {
            'identified_risks': risks,
            'overall_risk_score': min(100, risk_score),
            'risk_level': 'high' if risk_score > 50 else 'medium' if risk_score > 25 else 'low',
            'mitigation_strategies': self._suggest_risk_mitigations(risks)
        }
    
    def _suggest_risk_mitigations(self, risks: List[str]) -> List[str]:
        """Suggest risk mitigation strategies"""
        mitigations = []
        
        for risk in risks:
            if 'price sensitivity' in risk.lower():
                mitigations.append('Implement graduated pricing with lower entry points')
            elif 'premium pricing' in risk.lower():
                mitigations.append('Emphasize value proposition and unique features')
            elif 'complex pricing' in risk.lower():
                mitigations.append('Provide clear pricing calculator and examples')
        
        return mitigations
    
    def _assess_implementation_complexity(self, scenario: PricingScenario) -> Dict[str, Any]:
        """Assess implementation complexity"""
        
        complexity_factors = {
            PricingModel.FREEMIUM: 3,      # Medium complexity
            PricingModel.SUBSCRIPTION: 2,  # Low complexity
            PricingModel.PAY_PER_USE: 4,   # High complexity
            PricingModel.TIERED: 3,        # Medium complexity
            PricingModel.ENTERPRISE: 4,    # High complexity
            PricingModel.HYBRID: 5         # Very high complexity
        }
        
        base_complexity = complexity_factors.get(scenario.pricing_model, 3)
        
        # Add complexity for multiple target segments
        segment_complexity = len(scenario.target_segments) - 1
        
        total_complexity = min(5, base_complexity + segment_complexity)
        
        complexity_labels = {1: 'very_low', 2: 'low', 3: 'medium', 4: 'high', 5: 'very_high'}
        
        return {
            'complexity_score': total_complexity,
            'complexity_level': complexity_labels[total_complexity],
            'implementation_time_weeks': total_complexity * 2,
            'required_resources': ['product', 'engineering'] + (['data_analytics'] if total_complexity > 3 else [])
        }
    
    def _rank_scenarios(self, scenario_results: List[Dict[str, Any]], 
                       optimization_goals: Dict[OptimizationGoal, float]) -> List[Dict[str, Any]]:
        """Rank scenarios by optimization score"""
        
        # Sort by weighted optimization score
        ranked_scenarios = sorted(
            scenario_results,
            key=lambda x: x['weighted_optimization_score'],
            reverse=True
        )
        
        return ranked_scenarios
    
    def _generate_optimization_insights(self, scenario_results: List[Dict[str, Any]], 
                                       scenario_ranking: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate insights from optimization results"""
        
        insights = []
        
        if not scenario_ranking:
            return insights
        
        best_scenario = scenario_ranking[0]
        
        # Top scenario insights
        insights.append({
            'type': 'recommendation',
            'category': 'optimal_strategy',
            'title': f"Recommended Strategy: {best_scenario['pricing_model'].title()}",
            'description': f"Achieved highest optimization score of {best_scenario['weighted_optimization_score']:.1f}",
            'action_items': [
                'Develop detailed implementation plan',
                'Conduct A/B testing before full rollout',
                'Monitor key metrics during transition'
            ]
        })
        
        # Revenue opportunity insights
        revenue_scores = [result['projections']['revenue']['score'] for result in scenario_results]
        if max(revenue_scores) > 80:
            insights.append({
                'type': 'opportunity',
                'category': 'revenue_potential',
                'title': 'High Revenue Potential Identified',
                'description': 'Multiple scenarios show strong revenue generation capability',
                'action_items': [
                    'Focus on user acquisition to realize revenue potential',
                    'Ensure infrastructure can scale with projected growth'
                ]
            })
        
        # Risk insights
        high_risk_scenarios = [
            result for result in scenario_results 
            if result['risk_assessment']['overall_risk_score'] > 50
        ]
        if high_risk_scenarios:
            insights.append({
                'type': 'warning',
                'category': 'risk_management',
                'title': f"{len(high_risk_scenarios)} High-Risk Scenarios Identified",
                'description': 'Consider risk mitigation strategies before implementation',
                'action_items': [
                    'Implement gradual rollout strategy',
                    'Prepare contingency plans',
                    'Monitor customer feedback closely'
                ]
            })
        
        return insights
    
    def _create_implementation_plan(self, scenario_ranking: List[Dict[str, Any]], 
                                   optimization_insights: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create implementation plan for recommended strategy"""
        
        if not scenario_ranking:
            return {}
        
        recommended_scenario = scenario_ranking[0]
        
        implementation_phases = [
            {
                'phase': 'preparation',
                'duration_weeks': 2,
                'activities': [
                    'Finalize pricing structure details',
                    'Update billing system configuration',
                    'Prepare customer communication materials'
                ]
            },
            {
                'phase': 'pilot_testing',
                'duration_weeks': 4,
                'activities': [
                    'Launch A/B test with subset of users',
                    'Monitor conversion metrics',
                    'Collect customer feedback'
                ]
            },
            {
                'phase': 'gradual_rollout',
                'duration_weeks': 6,
                'activities': [
                    'Roll out to larger user segments',
                    'Monitor system performance',
                    'Adjust pricing based on learnings'
                ]
            },
            {
                'phase': 'full_implementation',
                'duration_weeks': 2,
                'activities': [
                    'Complete rollout to all users',
                    'Implement monitoring dashboards',
                    'Begin optimization iterations'
                ]
            }
        ]
        
        return {
            'recommended_scenario_id': recommended_scenario['scenario_id'],
            'implementation_phases': implementation_phases,
            'total_timeline_weeks': sum(phase['duration_weeks'] for phase in implementation_phases),
            'success_metrics': [
                'Monthly recurring revenue growth',
                'Customer acquisition rate',
                'Customer retention rate',
                'Net promoter score'
            ],
            'rollback_plan': {
                'triggers': ['Conversion rate drops > 25%', 'Customer complaints > threshold'],
                'rollback_time_hours': 4,
                'communication_plan': 'Pre-prepared customer notifications'
            }
        }
    
    def _perform_sensitivity_analysis(self, best_scenario: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform sensitivity analysis on the best scenario"""
        
        if not best_scenario:
            return {}
        
        # Analyze sensitivity to key parameters
        sensitivity_results = {}
        
        # Price sensitivity
        price_variations = [-0.2, -0.1, 0.1, 0.2]  # ±20%, ±10%
        price_impacts = []
        
        for variation in price_variations:
            impact_score = best_scenario['weighted_optimization_score'] * (1 + variation * 0.5)  # Assume 50% impact
            price_impacts.append({
                'price_change': f"{variation:+.1%}",
                'score_impact': impact_score,
                'score_change': impact_score - best_scenario['weighted_optimization_score']
            })
        
        sensitivity_results['price_sensitivity'] = price_impacts
        
        # Market size sensitivity
        market_variations = [-0.3, -0.15, 0.15, 0.3]  # ±30%, ±15%
        market_impacts = []
        
        for variation in market_variations:
            impact_score = best_scenario['weighted_optimization_score'] * (1 + variation * 0.3)
            market_impacts.append({
                'market_size_change': f"{variation:+.1%}",
                'score_impact': impact_score,
                'score_change': impact_score - best_scenario['weighted_optimization_score']
            })
        
        sensitivity_results['market_sensitivity'] = market_impacts
        
        return {
            'scenario_id': best_scenario['scenario_id'],
            'sensitivity_analysis': sensitivity_results,
            'most_sensitive_factor': 'price',  # Typically price is most sensitive
            'robustness_score': 75  # Score indicating how robust the strategy is to changes
        }