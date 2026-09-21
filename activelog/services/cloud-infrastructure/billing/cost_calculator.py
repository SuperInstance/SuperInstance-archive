"""
User-Friendly Cost Calculator
Helps users estimate costs before deploying resources with simple, clear pricing information.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import json
import logging
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

class UsagePattern(str, Enum):
    """Simple usage patterns for cost estimation"""
    ALWAYS_ON = "always_on"          # 24/7 usage
    BUSINESS_HOURS = "business_hours" # 8 hours/day, 5 days/week
    DEVELOPMENT = "development"       # 8 hours/day, 5 days/week, but can be stopped
    WEEKEND_ONLY = "weekend_only"    # Weekend projects
    CUSTOM = "custom"                 # User-defined hours

@dataclass
class CostEstimate:
    """Simple cost estimate breakdown"""
    hourly_cost: Decimal
    daily_cost: Decimal
    weekly_cost: Decimal
    monthly_cost: Decimal
    annual_cost: Decimal
    usage_pattern: str
    hours_per_month: int
    instance_type: str
    recommendations: List[str]

@dataclass
class SavingsOpportunity:
    """Potential savings recommendation"""
    title: str
    description: str
    monthly_savings: Decimal
    annual_savings: Decimal
    difficulty: str
    implementation_time: str

class CostCalculator:
    """User-friendly cost calculator for cloud resources"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pricing = config.get('billing', {}).get('pricing', {}).get('compute', {})
        
    def calculate_instance_cost(
        self,
        instance_type: str,
        usage_pattern: UsagePattern = UsagePattern.ALWAYS_ON,
        custom_hours_per_week: Optional[int] = None
    ) -> CostEstimate:
        """Calculate cost estimate for an instance with clear breakdown"""
        
        # Get base pricing (per minute)
        cost_per_minute = Decimal(str(self.pricing.get(instance_type, 0.01)))
        hourly_cost = cost_per_minute * 60
        
        # Calculate hours based on usage pattern
        hours_per_week = self._get_hours_per_week(usage_pattern, custom_hours_per_week)
        hours_per_month = hours_per_week * Decimal('4.33')  # Average weeks per month
        
        # Calculate costs
        daily_cost = hourly_cost * (hours_per_week / Decimal('7'))
        weekly_cost = hourly_cost * hours_per_week
        monthly_cost = hourly_cost * hours_per_month
        annual_cost = monthly_cost * Decimal('12')
        
        # Generate recommendations
        recommendations = self._generate_cost_recommendations(
            instance_type, usage_pattern, monthly_cost
        )
        
        return CostEstimate(
            hourly_cost=hourly_cost.quantize(Decimal('0.001')),
            daily_cost=daily_cost.quantize(Decimal('0.01')),
            weekly_cost=weekly_cost.quantize(Decimal('0.01')),
            monthly_cost=monthly_cost.quantize(Decimal('0.01')),
            annual_cost=annual_cost.quantize(Decimal('0.01')),
            usage_pattern=usage_pattern.value,
            hours_per_month=int(hours_per_month),
            instance_type=instance_type,
            recommendations=recommendations
        )
    
    def compare_instance_types(
        self,
        instance_types: List[str],
        usage_pattern: UsagePattern = UsagePattern.ALWAYS_ON,
        custom_hours_per_week: Optional[int] = None
    ) -> Dict[str, Any]:
        """Compare costs across different instance types"""
        
        estimates = {}
        for instance_type in instance_types:
            estimates[instance_type] = self.calculate_instance_cost(
                instance_type, usage_pattern, custom_hours_per_week
            )
        
        # Find best value
        sorted_by_monthly = sorted(
            estimates.items(), 
            key=lambda x: x[1].monthly_cost
        )
        
        cheapest = sorted_by_monthly[0]
        most_expensive = sorted_by_monthly[-1]
        
        # Calculate potential savings
        max_savings = most_expensive[1].monthly_cost - cheapest[1].monthly_cost
        
        return {
            'estimates': {k: asdict(v) for k, v in estimates.items()},
            'recommendations': {
                'most_cost_effective': {
                    'instance_type': cheapest[0],
                    'monthly_cost': f"${cheapest[1].monthly_cost:.2f}",
                    'annual_cost': f"${cheapest[1].annual_cost:.2f}"
                },
                'potential_savings': {
                    'max_monthly_savings': f"${max_savings:.2f}",
                    'max_annual_savings': f"${max_savings * Decimal('12'):.2f}",
                    'comparison': f"Choosing {cheapest[0]} over {most_expensive[0]} saves ${max_savings:.2f}/month"
                }
            },
            'summary': {
                'cheapest_option': cheapest[0],
                'most_expensive_option': most_expensive[0],
                'cost_range': f"${cheapest[1].monthly_cost:.2f} - ${most_expensive[1].monthly_cost:.2f}/month"
            }
        }
    
    def calculate_usage_pattern_savings(
        self,
        instance_type: str
    ) -> Dict[str, Any]:
        """Show potential savings from different usage patterns"""
        
        patterns = [
            UsagePattern.ALWAYS_ON,
            UsagePattern.BUSINESS_HOURS,
            UsagePattern.DEVELOPMENT,
            UsagePattern.WEEKEND_ONLY
        ]
        
        estimates = {}
        for pattern in patterns:
            estimates[pattern.value] = self.calculate_instance_cost(instance_type, pattern)
        
        # Calculate savings vs always-on
        always_on_cost = estimates['always_on'].monthly_cost
        savings = {}
        
        for pattern_name, estimate in estimates.items():
            if pattern_name != 'always_on':
                monthly_savings = always_on_cost - estimate.monthly_cost
                annual_savings = monthly_savings * Decimal('12')
                savings_percent = float(monthly_savings / always_on_cost * 100)
                
                savings[pattern_name] = {
                    'monthly_cost': f"${estimate.monthly_cost:.2f}",
                    'monthly_savings': f"${monthly_savings:.2f}",
                    'annual_savings': f"${annual_savings:.2f}",
                    'savings_percent': f"{savings_percent:.0f}%",
                    'hours_per_month': estimate.hours_per_month,
                    'description': self._get_pattern_description(pattern_name)
                }
        
        return {
            'instance_type': instance_type,
            'always_on_cost': f"${always_on_cost:.2f}/month",
            'usage_patterns': savings,
            'recommendations': [
                "Use 'development' pattern for test environments (save ~67%)",
                "Use 'business_hours' for office applications (save ~75%)",
                "Use 'weekend_only' for personal projects (save ~88%)"
            ],
            'implementation_tips': [
                "Set up automated start/stop schedules",
                "Use cloud functions to manage instance lifecycle",
                "Monitor usage patterns to optimize further"
            ]
        }
    
    def estimate_project_cost(
        self,
        project_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Estimate total project cost from configuration"""
        
        total_monthly = Decimal('0')
        total_annual = Decimal('0')
        component_costs = {}
        
        # Process each component
        for component_name, component_config in project_config.items():
            instance_type = component_config.get('instance_type', 't3.medium')
            quantity = component_config.get('quantity', 1)
            usage_pattern = UsagePattern(component_config.get('usage_pattern', 'always_on'))
            
            # Calculate cost for one instance
            estimate = self.calculate_instance_cost(instance_type, usage_pattern)
            
            # Multiply by quantity
            component_monthly = estimate.monthly_cost * quantity
            component_annual = estimate.annual_cost * quantity
            
            total_monthly += component_monthly
            total_annual += component_annual
            
            component_costs[component_name] = {
                'instance_type': instance_type,
                'quantity': quantity,
                'usage_pattern': usage_pattern.value,
                'monthly_cost_per_instance': f"${estimate.monthly_cost:.2f}",
                'total_monthly_cost': f"${component_monthly:.2f}",
                'total_annual_cost': f"${component_annual:.2f}",
                'percentage_of_total': f"{float(component_monthly / total_monthly * 100):.1f}%" if total_monthly > 0 else "0%"
            }
        
        # Generate project-level recommendations
        project_recommendations = self._generate_project_recommendations(
            component_costs, total_monthly
        )
        
        return {
            'project_summary': {
                'total_monthly_cost': f"${total_monthly:.2f}",
                'total_annual_cost': f"${total_annual:.2f}",
                'number_of_components': len(component_costs),
                'total_instances': sum(config.get('quantity', 1) for config in project_config.values())
            },
            'component_breakdown': component_costs,
            'cost_optimization': project_recommendations,
            'budget_planning': {
                'conservative_estimate': f"${total_monthly * Decimal('1.2'):.2f}/month",  # 20% buffer
                'aggressive_estimate': f"${total_monthly * Decimal('0.8'):.2f}/month",   # 20% savings
                'break_even_timeline': "Immediate (pay-as-you-go)",
                'scaling_considerations': [
                    "Costs scale linearly with usage",
                    "Consider reserved instances for 40%+ utilization",
                    "Monitor and optimize monthly"
                ]
            }
        }
    
    def get_savings_recommendations(
        self,
        current_spending: Decimal,
        instance_types_used: List[str],
        usage_patterns: Dict[str, str]
    ) -> List[SavingsOpportunity]:
        """Generate personalized savings recommendations"""
        
        recommendations = []
        
        # Right-sizing recommendations
        for instance_type in instance_types_used:
            if instance_type in ['t3.large', 't3.xlarge', 'c5.xlarge']:
                smaller_type = self._suggest_smaller_instance(instance_type)
                if smaller_type:
                    current_cost = self.calculate_instance_cost(instance_type, UsagePattern.ALWAYS_ON)
                    smaller_cost = self.calculate_instance_cost(smaller_type, UsagePattern.ALWAYS_ON)
                    savings = current_cost.monthly_cost - smaller_cost.monthly_cost
                    
                    recommendations.append(SavingsOpportunity(
                        title=f"Right-size {instance_type} instances",
                        description=f"Consider downsizing to {smaller_type} if current utilization is low",
                        monthly_savings=savings,
                        annual_savings=savings * Decimal('12'),
                        difficulty="Easy",
                        implementation_time="5 minutes per instance"
                    ))
        
        # Usage pattern optimization
        if current_spending > 200:  # Only for significant spending
            recommendations.append(SavingsOpportunity(
                title="Optimize development instance schedules",
                description="Stop development/testing instances during nights and weekends",
                monthly_savings=current_spending * Decimal('0.4'),  # 40% potential savings
                annual_savings=current_spending * Decimal('0.4') * Decimal('12'),
                difficulty="Medium",
                implementation_time="30 minutes setup"
            ))
        
        # Reserved instance recommendations
        if current_spending > 500:  # For consistent high usage
            ri_savings = current_spending * Decimal('0.3')  # 30% savings estimate
            recommendations.append(SavingsOpportunity(
                title="Consider Reserved Instances",
                description="Lock in lower rates for consistent workloads with 1-year commitments",
                monthly_savings=ri_savings,
                annual_savings=ri_savings * Decimal('12'),
                difficulty="Easy",
                implementation_time="10 minutes per instance type"
            ))
        
        # Sort by potential savings
        recommendations.sort(key=lambda x: x.monthly_savings, reverse=True)
        
        return recommendations[:5]  # Top 5 recommendations
    
    # Helper methods
    def _get_hours_per_week(self, usage_pattern: UsagePattern, custom_hours: Optional[int]) -> Decimal:
        """Get hours per week for different usage patterns"""
        
        if usage_pattern == UsagePattern.ALWAYS_ON:
            return Decimal('168')  # 24/7
        elif usage_pattern == UsagePattern.BUSINESS_HOURS:
            return Decimal('40')   # 8h/day * 5 days
        elif usage_pattern == UsagePattern.DEVELOPMENT:
            return Decimal('40')   # Same as business hours but can be optimized
        elif usage_pattern == UsagePattern.WEEKEND_ONLY:
            return Decimal('20')   # 10h/day * 2 days
        elif usage_pattern == UsagePattern.CUSTOM and custom_hours:
            return Decimal(str(custom_hours))
        else:
            return Decimal('168')  # Default to always-on
    
    def _generate_cost_recommendations(
        self,
        instance_type: str,
        usage_pattern: UsagePattern,
        monthly_cost: Decimal
    ) -> List[str]:
        """Generate cost optimization recommendations"""
        
        recommendations = []
        
        # Usage pattern recommendations
        if usage_pattern == UsagePattern.ALWAYS_ON and monthly_cost > 100:
            recommendations.append("💡 Consider if this instance needs to run 24/7 - you could save 60-80% with scheduled usage")
        
        # Instance size recommendations
        if instance_type in ['t3.xlarge', 't3.2xlarge']:
            recommendations.append("🔍 Monitor CPU usage - you might save money with a smaller instance if utilization is low")
        
        # Reserved instance recommendations
        if monthly_cost > 50 and usage_pattern == UsagePattern.ALWAYS_ON:
            annual_savings = monthly_cost * Decimal('12') * Decimal('0.3')  # 30% RI savings
            recommendations.append(f"💰 Consider Reserved Instances for ~${annual_savings:.0f}/year savings on consistent workloads")
        
        # Spot instance recommendations for fault-tolerant workloads
        if instance_type.startswith('c5') and monthly_cost > 30:
            recommendations.append("⚡ For fault-tolerant workloads, Spot Instances could save 60-90% of costs")
        
        # General optimization
        if monthly_cost > 200:
            recommendations.append("📊 Set up cost monitoring alerts to catch unexpected usage spikes early")
        
        return recommendations[:3]  # Limit to top 3 recommendations
    
    def _generate_project_recommendations(
        self,
        component_costs: Dict[str, Any],
        total_monthly: Decimal
    ) -> List[str]:
        """Generate project-level cost optimization recommendations"""
        
        recommendations = []
        
        # Find highest cost component
        highest_cost_component = max(
            component_costs.items(),
            key=lambda x: float(x[1]['total_monthly_cost'].replace('$', ''))
        )
        
        recommendations.append(
            f"🎯 Focus optimization on '{highest_cost_component[0]}' - it's your highest cost component"
        )
        
        # Check for development environments
        dev_components = [name for name, config in component_costs.items() 
                         if 'dev' in name.lower() or 'test' in name.lower()]
        
        if dev_components:
            recommendations.append(
                f"🛠️ Consider 'development' usage pattern for {', '.join(dev_components)} to save ~67%"
            )
        
        # Overall budget recommendations
        if total_monthly > 1000:
            recommendations.append("💼 Consider speaking with a cloud cost optimization specialist")
        elif total_monthly > 500:
            recommendations.append("📈 Set up detailed cost tracking and monthly reviews")
        else:
            recommendations.append("✅ Your projected costs look reasonable for a small-medium project")
        
        return recommendations
    
    def _get_pattern_description(self, pattern_name: str) -> str:
        """Get human-readable description of usage patterns"""
        
        descriptions = {
            'business_hours': '8 hours/day, Monday-Friday (typical office application)',
            'development': '8 hours/day, Monday-Friday (can be stopped when not in use)',
            'weekend_only': '10 hours each weekend day (personal projects, batch jobs)',
            'custom': 'User-defined schedule'
        }
        
        return descriptions.get(pattern_name, 'Custom usage pattern')
    
    def _suggest_smaller_instance(self, instance_type: str) -> Optional[str]:
        """Suggest a smaller instance type for right-sizing"""
        
        downsizing_map = {
            't3.2xlarge': 't3.xlarge',
            't3.xlarge': 't3.large',
            't3.large': 't3.medium',
            't3.medium': 't3.small',
            'c5.2xlarge': 'c5.xlarge',
            'c5.xlarge': 'c5.large',
            'c5.large': 't3.medium',  # Cross-family recommendation
        }
        
        return downsizing_map.get(instance_type)
    
    def get_pricing_summary(self) -> Dict[str, Any]:
        """Get a simple pricing summary for popular instance types"""
        
        popular_instances = ['t3.nano', 't3.micro', 't3.small', 't3.medium', 't3.large']
        pricing_summary = {}
        
        for instance_type in popular_instances:
            if instance_type in self.pricing:
                estimate = self.calculate_instance_cost(instance_type, UsagePattern.ALWAYS_ON)
                pricing_summary[instance_type] = {
                    'hourly': f"${estimate.hourly_cost:.3f}",
                    'daily': f"${estimate.daily_cost:.2f}",
                    'monthly': f"${estimate.monthly_cost:.2f}",
                    'use_case': self._get_instance_use_case(instance_type)
                }
        
        return {
            'popular_instances': pricing_summary,
            'pricing_notes': [
                "Prices shown are for 24/7 usage (always-on)",
                "Actual costs depend on your usage pattern", 
                "Development/testing workloads can save 60-80% with scheduling",
                "Reserved instances offer ~30% savings for consistent workloads"
            ],
            'cost_optimization_tips': [
                "Start small - you can always upgrade instance size later",
                "Use development usage patterns for non-production workloads",
                "Monitor your actual usage and right-size accordingly",
                "Set up billing alerts to avoid surprises"
            ]
        }
    
    def _get_instance_use_case(self, instance_type: str) -> str:
        """Get recommended use case for instance type"""
        
        use_cases = {
            't3.nano': 'Light workloads, microservices, low-traffic websites',
            't3.micro': 'Small applications, development environments',
            't3.small': 'Small databases, web servers, development',
            't3.medium': 'General purpose applications, medium traffic websites',
            't3.large': 'High-traffic applications, larger databases',
            't3.xlarge': 'Enterprise applications, high-performance workloads',
            'c5.large': 'CPU-intensive applications, batch processing',
            'c5.xlarge': 'High-performance computing, scientific applications'
        }
        
        return use_cases.get(instance_type, 'General purpose computing')
        