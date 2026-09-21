"""
User-Friendly Finance Dashboard
Provides intuitive financial management tools with clear visualizations and easy-to-understand metrics.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import json
import logging
from dataclasses import dataclass, asdict
import calendar

logger = logging.getLogger(__name__)

class BudgetStatus(str, Enum):
    """Budget status indicators"""
    HEALTHY = "healthy"          # Under 70% of budget
    WARNING = "warning"          # 70-90% of budget  
    CRITICAL = "critical"        # 90-100% of budget
    OVER_BUDGET = "over_budget"  # Over 100% of budget

class CostCategory(str, Enum):
    """User-friendly cost categories"""
    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORKING = "networking"
    MONITORING = "monitoring"
    SUPPORT = "support"
    OTHER = "other"

@dataclass
class SimpleCostSummary:
    """Simple, easy-to-understand cost summary"""
    current_month_cost: Decimal
    last_month_cost: Decimal
    cost_change_amount: Decimal
    cost_change_percent: float
    cost_trend: str  # "increasing", "decreasing", "stable"
    daily_average: Decimal
    projected_month_end: Decimal
    days_remaining: int

@dataclass
class BudgetAlert:
    """User-friendly budget alert"""
    severity: BudgetStatus
    title: str
    message: str
    amount_spent: Decimal
    budget_limit: Decimal
    percentage_used: float
    days_left_in_period: int
    suggested_action: str
    icon: str

@dataclass
class CostInsight:
    """Actionable cost insight"""
    category: str
    title: str
    description: str
    potential_savings: Decimal
    difficulty: str  # "easy", "medium", "hard"
    time_to_implement: str
    priority: str  # "high", "medium", "low"
    action_steps: List[str]

@dataclass
class FinancialHealthScore:
    """Overall financial health score"""
    score: int  # 0-100
    grade: str  # A+, A, B+, B, C+, C, D, F
    description: str
    key_strengths: List[str]
    improvement_areas: List[str]
    next_steps: List[str]

class UserFriendlyFinanceDashboard:
    """User-friendly finance dashboard with intuitive metrics and visualizations"""
    
    def __init__(self, database_manager, billing_engine, usage_analytics):
        self.database_manager = database_manager
        self.billing_engine = billing_engine
        self.usage_analytics = usage_analytics
    
    async def get_financial_overview(self, user_id: str) -> Dict[str, Any]:
        """Get a comprehensive, easy-to-understand financial overview"""
        
        try:
            # Get current month data
            now = datetime.now()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
            
            # Get last month data
            last_month_end = month_start - timedelta(seconds=1)
            last_month_start = last_month_end.replace(day=1)
            
            # Get billing data
            current_records = await self._get_billing_records(user_id, month_start, now)
            last_month_records = await self._get_billing_records(user_id, last_month_start, last_month_end)
            
            # Calculate summary
            cost_summary = await self._calculate_cost_summary(
                current_records, last_month_records, month_start, now
            )
            
            # Get budget alerts
            budget_alerts = await self._get_budget_alerts(user_id, cost_summary.current_month_cost)
            
            # Get cost insights
            cost_insights = await self._generate_cost_insights(user_id, current_records)
            
            # Calculate financial health score
            health_score = await self._calculate_financial_health_score(
                user_id, cost_summary, budget_alerts, cost_insights
            )
            
            # Get spending by category
            category_breakdown = await self._get_category_breakdown(current_records)
            
            # Get daily spending trend
            daily_trend = await self._get_daily_spending_trend(current_records, month_start, now)
            
            return {
                'overview': {
                    'current_month': f"${cost_summary.current_month_cost:.2f}",
                    'vs_last_month': f"{cost_summary.cost_change_percent:+.1f}%",
                    'trend_direction': cost_summary.cost_trend,
                    'daily_average': f"${cost_summary.daily_average:.2f}",
                    'projected_month_end': f"${cost_summary.projected_month_end:.2f}",
                    'days_remaining': cost_summary.days_remaining
                },
                'cost_summary': asdict(cost_summary),
                'budget_alerts': [asdict(alert) for alert in budget_alerts],
                'cost_insights': [asdict(insight) for insight in cost_insights[:5]],  # Top 5
                'financial_health': asdict(health_score),
                'spending_by_category': category_breakdown,
                'daily_trend': daily_trend,
                'quick_actions': await self._get_quick_actions(user_id, cost_insights),
                'helpful_tips': await self._get_helpful_tips(cost_summary, budget_alerts)
            }
            
        except Exception as e:
            logger.error(f"Error generating financial overview: {e}")
            return {
                'error': 'Unable to load financial overview',
                'message': 'Please try again later or contact support if the problem persists.'
            }
    
    async def get_budget_management(self, user_id: str) -> Dict[str, Any]:
        """Get user-friendly budget management interface"""
        
        try:
            user = await self._get_user(user_id)
            current_spend = await self._get_current_month_spend(user_id)
            
            # Get or create default budgets
            budgets = await self._get_user_budgets(user_id)
            if not budgets:
                budgets = await self._create_default_budgets(user_id, current_spend)
            
            # Calculate budget status
            budget_status = []
            for budget in budgets:
                status = self._calculate_budget_status(current_spend, budget['limit'])
                budget_status.append({
                    'name': budget['name'],
                    'current_spend': f"${current_spend:.2f}",
                    'budget_limit': f"${budget['limit']:.2f}",
                    'remaining': f"${max(0, budget['limit'] - current_spend):.2f}",
                    'percentage_used': min(100, (current_spend / budget['limit'] * 100)),
                    'status': status.value,
                    'status_color': self._get_status_color(status),
                    'days_remaining': (datetime.now().replace(day=28) + timedelta(days=4)).replace(day=1) - datetime.now(),
                    'projected_end_spend': await self._project_month_end_spend(user_id),
                    'recommendations': await self._get_budget_recommendations(status, current_spend, budget['limit'])
                })
            
            return {
                'budgets': budget_status,
                'spending_velocity': await self._calculate_spending_velocity(user_id),
                'cost_controls': await self._get_available_cost_controls(user_id),
                'savings_opportunities': await self._get_immediate_savings(user_id),
                'budget_tools': {
                    'set_alerts': True,
                    'automatic_controls': True,
                    'spending_limits': True,
                    'approval_workflows': True
                }
            }
            
        except Exception as e:
            logger.error(f"Error in budget management: {e}")
            return {'error': 'Unable to load budget information'}
    
    async def get_cost_optimization_guide(self, user_id: str) -> Dict[str, Any]:
        """Get personalized cost optimization guide"""
        
        try:
            # Get recent billing data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            billing_records = await self._get_billing_records(user_id, start_date, end_date)
            utilization_data = await self.usage_analytics.analyze_resource_utilization(
                user_id, start_date, end_date
            )
            
            # Generate optimization recommendations
            recommendations = []
            
            # Right-sizing recommendations
            underutilized = [u for u in utilization_data if u.utilization_percent < 30]
            for util in underutilized[:3]:  # Top 3 underutilized
                monthly_savings = util.cost_efficiency_score * 0.4  # Estimate 40% savings
                recommendations.append({
                    'title': f"Right-size {util.resource_type} instance",
                    'description': f"Instance {util.resource_id[:8]}... is only using {util.utilization_percent:.1f}% of its capacity",
                    'potential_savings': f"${monthly_savings:.2f}/month",
                    'difficulty': 'easy',
                    'time_to_implement': '5 minutes',
                    'impact': 'high' if monthly_savings > 50 else 'medium',
                    'steps': [
                        f"Navigate to your {util.resource_type} instances",
                        f"Select instance {util.resource_id[:8]}...",
                        "Choose 'Resize Instance'",
                        f"Select a smaller instance type (t3.small → t3.micro)",
                        "Apply changes and monitor performance"
                    ],
                    'risk_level': 'low',
                    'category': 'right_sizing'
                })
            
            # Scheduling recommendations
            total_cost = sum(self._extract_cost(record) for record in billing_records)
            if total_cost > 100:  # Only for significant spend
                recommendations.append({
                    'title': 'Schedule non-critical workloads',
                    'description': 'Run development and testing workloads during off-peak hours',
                    'potential_savings': f"${total_cost * 0.15:.2f}/month",
                    'difficulty': 'medium',
                    'time_to_implement': '30 minutes',
                    'impact': 'medium',
                    'steps': [
                        "Identify development/testing instances",
                        "Set up automated start/stop schedules",
                        "Configure instances to stop at 6 PM and start at 8 AM",
                        "Monitor savings in your next bill"
                    ],
                    'risk_level': 'low',
                    'category': 'scheduling'
                })
            
            # Reserved instances for stable workloads
            long_running = [u for u in utilization_data if u.total_runtime_minutes > 20160]  # >2 weeks
            if long_running:
                potential_ri_savings = sum(u.cost_efficiency_score * 0.3 for u in long_running)
                recommendations.append({
                    'title': 'Consider Reserved Instances',
                    'description': f'You have {len(long_running)} long-running instances that could benefit from reserved pricing',
                    'potential_savings': f"${potential_ri_savings:.2f}/month",
                    'difficulty': 'easy',
                    'time_to_implement': '10 minutes',
                    'impact': 'high',
                    'steps': [
                        "Review your consistently running instances",
                        "Purchase 1-year Reserved Instances for stable workloads",
                        "Start with your highest-cost instances",
                        "Monitor usage to ensure commitment utilization"
                    ],
                    'risk_level': 'low',
                    'category': 'reserved_instances'
                })
            
            # Sort by potential savings
            recommendations.sort(key=lambda x: float(x['potential_savings'].replace('$', '').replace('/month', '')), reverse=True)
            
            return {
                'optimization_score': self._calculate_optimization_score(utilization_data),
                'total_potential_savings': f"${sum(float(r['potential_savings'].replace('$', '').replace('/month', '')) for r in recommendations):.2f}/month",
                'recommendations': recommendations,
                'quick_wins': [r for r in recommendations if r['difficulty'] == 'easy'][:3],
                'optimization_categories': {
                    'right_sizing': len([r for r in recommendations if r['category'] == 'right_sizing']),
                    'scheduling': len([r for r in recommendations if r['category'] == 'scheduling']),  
                    'reserved_instances': len([r for r in recommendations if r['category'] == 'reserved_instances']),
                },
                'implementation_guide': {
                    'getting_started': "Start with 'easy' recommendations for immediate impact",
                    'best_practices': [
                        "Implement one change at a time",
                        "Monitor performance after each change", 
                        "Set up alerts to track savings",
                        "Review and adjust monthly"
                    ],
                    'support_resources': [
                        "Cost optimization documentation",
                        "Instance sizing calculator", 
                        "Reserved instance planner",
                        "24/7 support chat"
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating optimization guide: {e}")
            return {'error': 'Unable to load optimization guide'}
    
    async def get_simple_invoice_view(self, user_id: str, month: Optional[str] = None) -> Dict[str, Any]:
        """Get a simple, easy-to-understand invoice view"""
        
        try:
            # Parse month or use current
            if month:
                invoice_date = datetime.strptime(month, '%Y-%m')
            else:
                invoice_date = datetime.now()
                
            month_start = invoice_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
            
            billing_records = await self._get_billing_records(user_id, month_start, month_end)
            
            # Group by service and instance type
            service_summary = {}
            instance_summary = {}
            daily_breakdown = {}
            
            total_cost = Decimal('0')
            total_hours = 0
            
            for record in billing_records:
                cost = self._extract_cost(record)
                duration = self._extract_duration(record)
                service = self._extract_service_type(record)
                instance_type = self._extract_instance_type(record)
                date_key = self._extract_date(record).strftime('%Y-%m-%d')
                
                total_cost += cost
                total_hours += duration / 60
                
                # Service summary
                if service not in service_summary:
                    service_summary[service] = {'cost': Decimal('0'), 'hours': 0, 'instances': set()}
                service_summary[service]['cost'] += cost
                service_summary[service]['hours'] += duration / 60
                service_summary[service]['instances'].add(self._extract_instance_id(record))
                
                # Instance type summary
                if instance_type not in instance_summary:
                    instance_summary[instance_type] = {'cost': Decimal('0'), 'hours': 0, 'count': 0}
                instance_summary[instance_type]['cost'] += cost
                instance_summary[instance_type]['hours'] += duration / 60
                instance_summary[instance_type]['count'] += 1
                
                # Daily breakdown
                if date_key not in daily_breakdown:
                    daily_breakdown[date_key] = Decimal('0')
                daily_breakdown[date_key] += cost
            
            # Format service summary
            formatted_services = []
            for service, data in service_summary.items():
                formatted_services.append({
                    'name': service.title(),
                    'cost': f"${data['cost']:.2f}",
                    'percentage': f"{(data['cost'] / total_cost * 100):.1f}%" if total_cost > 0 else "0%",
                    'hours': f"{data['hours']:.1f}h",
                    'instances': len(data['instances']),
                    'avg_hourly_rate': f"${(data['cost'] / data['hours']):.3f}/h" if data['hours'] > 0 else "$0/h"
                })
            
            # Sort by cost
            formatted_services.sort(key=lambda x: float(x['cost'].replace('$', '')), reverse=True)
            
            return {
                'invoice_summary': {
                    'month': invoice_date.strftime('%B %Y'),
                    'total_cost': f"${total_cost:.2f}",
                    'total_hours': f"{total_hours:.1f}h",
                    'average_daily_cost': f"${(total_cost / max(1, (month_end - month_start).days)):.2f}",
                    'billing_period': f"{month_start.strftime('%b %d')} - {month_end.strftime('%b %d, %Y')}"
                },
                'cost_by_service': formatted_services,
                'daily_spending': [
                    {
                        'date': date,
                        'cost': f"${cost:.2f}",
                        'day_of_week': datetime.strptime(date, '%Y-%m-%d').strftime('%A')
                    }
                    for date, cost in sorted(daily_breakdown.items())
                ],
                'payment_info': await self._get_payment_info(user_id),
                'billing_summary': {
                    'line_items': len(billing_records),
                    'unique_resources': len(set(self._extract_instance_id(r) for r in billing_records)),
                    'peak_daily_cost': max(daily_breakdown.values()) if daily_breakdown else Decimal('0'),
                    'lowest_daily_cost': min(daily_breakdown.values()) if daily_breakdown else Decimal('0')
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating invoice view: {e}")
            return {'error': 'Unable to load invoice'}
    
    # Helper methods
    async def _calculate_cost_summary(self, current_records, last_month_records, month_start, now) -> SimpleCostSummary:
        """Calculate simple cost summary"""
        
        current_cost = sum(self._extract_cost(r) for r in current_records)
        last_month_cost = sum(self._extract_cost(r) for r in last_month_records)
        
        cost_change = current_cost - last_month_cost
        cost_change_percent = float((cost_change / last_month_cost * 100) if last_month_cost > 0 else 0)
        
        # Determine trend
        if abs(cost_change_percent) < 5:
            trend = "stable"
        elif cost_change_percent > 0:
            trend = "increasing"
        else:
            trend = "decreasing"
        
        # Calculate daily average and projection
        days_elapsed = (now - month_start).days + 1
        daily_average = current_cost / days_elapsed if days_elapsed > 0 else Decimal('0')
        
        # Project to month end
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
        total_days_in_month = (month_end - month_start).days + 1
        days_remaining = total_days_in_month - days_elapsed
        projected_month_end = current_cost + (daily_average * days_remaining)
        
        return SimpleCostSummary(
            current_month_cost=current_cost,
            last_month_cost=last_month_cost,
            cost_change_amount=cost_change,
            cost_change_percent=cost_change_percent,
            cost_trend=trend,
            daily_average=daily_average,
            projected_month_end=projected_month_end,
            days_remaining=days_remaining
        )
    
    async def _get_budget_alerts(self, user_id: str, current_spend: Decimal) -> List[BudgetAlert]:
        """Generate user-friendly budget alerts"""
        
        user = await self._get_user(user_id)
        monthly_budget = getattr(user, 'monthly_budget', None) or Decimal('1000')  # Default budget
        
        percentage_used = float(current_spend / monthly_budget * 100)
        days_left = (datetime.now().replace(day=28) + timedelta(days=4)).replace(day=1) - datetime.now()
        days_left_count = days_left.days
        
        alerts = []
        
        if percentage_used >= 100:
            alerts.append(BudgetAlert(
                severity=BudgetStatus.OVER_BUDGET,
                title="⚠️ Over Budget",
                message=f"You've exceeded your monthly budget by ${current_spend - monthly_budget:.2f}",
                amount_spent=current_spend,
                budget_limit=monthly_budget,
                percentage_used=percentage_used,
                days_left_in_period=days_left_count,
                suggested_action="Review and optimize your resources immediately, or increase your budget",
                icon="🚨"
            ))
        elif percentage_used >= 90:
            alerts.append(BudgetAlert(
                severity=BudgetStatus.CRITICAL,
                title="Budget Alert",
                message=f"You've used {percentage_used:.0f}% of your monthly budget",
                amount_spent=current_spend,
                budget_limit=monthly_budget,
                percentage_used=percentage_used,
                days_left_in_period=days_left_count,
                suggested_action="Consider stopping non-essential resources or increasing your budget",
                icon="⚠️"
            ))
        elif percentage_used >= 70:
            alerts.append(BudgetAlert(
                severity=BudgetStatus.WARNING,
                title="Budget Warning",
                message=f"You've used {percentage_used:.0f}% of your budget with {days_left_count} days remaining",
                amount_spent=current_spend,
                budget_limit=monthly_budget,
                percentage_used=percentage_used,
                days_left_in_period=days_left_count,
                suggested_action="Monitor your spending closely and consider optimizing resources",
                icon="📊"
            ))
        else:
            alerts.append(BudgetAlert(
                severity=BudgetStatus.HEALTHY,
                title="Budget on Track",
                message=f"You're using your budget efficiently ({percentage_used:.0f}% used)",
                amount_spent=current_spend,
                budget_limit=monthly_budget,
                percentage_used=percentage_used,
                days_left_in_period=days_left_count,
                suggested_action="Keep monitoring your spending patterns",
                icon="✅"
            ))
        
        return alerts
    
    async def _generate_cost_insights(self, user_id: str, billing_records) -> List[CostInsight]:
        """Generate actionable cost insights"""
        
        insights = []
        
        if not billing_records:
            return insights
        
        # Analyze spending patterns
        total_cost = sum(self._extract_cost(r) for r in billing_records)
        
        # Check for high-cost resources
        instance_costs = {}
        for record in billing_records:
            instance_id = self._extract_instance_id(record)
            cost = self._extract_cost(record)
            if instance_id not in instance_costs:
                instance_costs[instance_id] = Decimal('0')
            instance_costs[instance_id] += cost
        
        # Find most expensive instance
        if instance_costs:
            most_expensive = max(instance_costs.items(), key=lambda x: x[1])
            if most_expensive[1] > total_cost * Decimal('0.3'):  # >30% of total
                insights.append(CostInsight(
                    category="high_cost_resource",
                    title=f"High-cost instance detected",
                    description=f"Instance {most_expensive[0][:8]}... accounts for {(most_expensive[1]/total_cost*100):.0f}% of your spending",
                    potential_savings=most_expensive[1] * Decimal('0.3'),
                    difficulty="easy",
                    time_to_implement="5 minutes",
                    priority="high",
                    action_steps=[
                        "Review the instance utilization",
                        "Consider right-sizing if underutilized",
                        "Check if the workload can be optimized",
                        "Consider reserved instances if consistently used"
                    ]
                ))
        
        # Check for weekend usage
        weekend_cost = Decimal('0')
        weekday_cost = Decimal('0')
        
        for record in billing_records:
            date = self._extract_date(record)
            cost = self._extract_cost(record)
            if date.weekday() >= 5:  # Saturday or Sunday
                weekend_cost += cost
            else:
                weekday_cost += cost
        
        if weekend_cost > total_cost * Decimal('0.2'):  # >20% on weekends
            insights.append(CostInsight(
                category="weekend_usage",
                title="High weekend usage detected",
                description=f"${weekend_cost:.2f} ({(weekend_cost/total_cost*100):.0f}%) spent on weekends",
                potential_savings=weekend_cost * Decimal('0.7'),
                difficulty="medium",
                time_to_implement="30 minutes",
                priority="medium",
                action_steps=[
                    "Identify development/testing instances",
                    "Set up weekend shutdown schedules",
                    "Keep only production instances running",
                    "Monitor savings in next bill"
                ]
            ))
        
        return insights
    
    async def _calculate_financial_health_score(self, user_id: str, cost_summary: SimpleCostSummary, 
                                               budget_alerts: List[BudgetAlert], 
                                               cost_insights: List[CostInsight]) -> FinancialHealthScore:
        """Calculate overall financial health score"""
        
        score = 100
        issues = []
        strengths = []
        
        # Budget adherence (40 points)
        budget_alert = budget_alerts[0] if budget_alerts else None
        if budget_alert:
            if budget_alert.severity == BudgetStatus.OVER_BUDGET:
                score -= 40
                issues.append("Over budget")
            elif budget_alert.severity == BudgetStatus.CRITICAL:
                score -= 30
                issues.append("Near budget limit")
            elif budget_alert.severity == BudgetStatus.WARNING:
                score -= 15
                issues.append("High budget usage")
            else:
                strengths.append("Within budget")
        
        # Cost trend (30 points)
        if cost_summary.cost_trend == "increasing" and cost_summary.cost_change_percent > 20:
            score -= 25
            issues.append("Rapidly increasing costs")
        elif cost_summary.cost_trend == "increasing" and cost_summary.cost_change_percent > 10:
            score -= 15
            issues.append("Rising costs")
        elif cost_summary.cost_trend == "decreasing":
            strengths.append("Decreasing costs")
        else:
            strengths.append("Stable costs")
        
        # Optimization opportunities (30 points)
        high_priority_insights = [i for i in cost_insights if i.priority == "high"]
        if len(high_priority_insights) > 2:
            score -= 20
            issues.append("Multiple optimization opportunities")
        elif len(high_priority_insights) > 0:
            score -= 10
            issues.append("Some optimization opportunities")
        else:
            strengths.append("Well-optimized spending")
        
        # Determine grade
        if score >= 95:
            grade = "A+"
        elif score >= 90:
            grade = "A"
        elif score >= 85:
            grade = "B+"
        elif score >= 80:
            grade = "B"
        elif score >= 75:
            grade = "C+"
        elif score >= 70:
            grade = "C"
        elif score >= 60:
            grade = "D"
        else:
            grade = "F"
        
        # Generate description and next steps
        if score >= 85:
            description = "Excellent financial management! Your cloud spending is well-controlled and optimized."
            next_steps = ["Continue monitoring trends", "Review monthly for new optimizations"]
        elif score >= 70:
            description = "Good financial health with room for improvement. Focus on the identified areas."
            next_steps = ["Address high-priority cost insights", "Set up budget alerts", "Review resource utilization"]
        else:
            description = "Your cloud spending needs attention. Take immediate action to optimize costs."
            next_steps = ["Review and optimize high-cost resources", "Set strict budget limits", "Consider professional consultation"]
        
        return FinancialHealthScore(
            score=max(0, score),
            grade=grade,
            description=description,
            key_strengths=strengths,
            improvement_areas=issues,
            next_steps=next_steps
        )
    
    # Database and utility methods
    async def _get_billing_records(self, user_id: str, start_date: datetime, end_date: datetime):
        """Get billing records"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            query = """
                SELECT * FROM billing_records 
                WHERE user_id = ? AND start_time >= ? AND end_time <= ?
                ORDER BY start_time DESC
            """
            cursor = await conn.execute(query, (user_id, start_date, end_date))
            return await cursor.fetchall()
    
    async def _get_user(self, user_id: str):
        """Get user information"""
        return await self.database_manager.get_user(user_id)
    
    def _extract_cost(self, record) -> Decimal:
        """Extract cost from record (handle tuple format)"""
        if hasattr(record, 'total_cost'):
            return record.total_cost
        elif hasattr(record, 'cost'):
            return record.cost
        else:
            return Decimal(str(record[8])) if len(record) > 8 else Decimal('0')
    
    def _extract_duration(self, record) -> int:
        """Extract duration from record"""
        if hasattr(record, 'duration_minutes'):
            return record.duration_minutes
        else:
            return record[6] if len(record) > 6 else 0
    
    def _extract_service_type(self, record) -> str:
        """Extract service type from record"""
        if hasattr(record, 'service_type'):
            return record.service_type or 'compute'
        else:
            return record[9] if len(record) > 9 else 'compute'
    
    def _extract_instance_type(self, record) -> str:
        """Extract instance type from record"""
        if hasattr(record, 'instance_type'):
            return record.instance_type or 'unknown'
        else:
            return record[3] if len(record) > 3 else 'unknown'
    
    def _extract_instance_id(self, record) -> str:
        """Extract instance ID from record"""
        if hasattr(record, 'instance_id'):
            return record.instance_id
        else:
            return record[2] if len(record) > 2 else 'unknown'
    
    def _extract_date(self, record) -> datetime:
        """Extract date from record"""
        if hasattr(record, 'start_time'):
            return record.start_time
        else:
            date_str = record[4] if len(record) > 4 else datetime.now().isoformat()
            return datetime.fromisoformat(date_str) if isinstance(date_str, str) else date_str
    
    async def _get_category_breakdown(self, billing_records) -> List[Dict[str, Any]]:
        """Get spending breakdown by category"""
        categories = {
            'compute': Decimal('0'),
            'storage': Decimal('0'),
            'networking': Decimal('0'),
            'other': Decimal('0')
        }
        
        total = Decimal('0')
        for record in billing_records:
            cost = self._extract_cost(record)
            service = self._extract_service_type(record)
            total += cost
            
            if service in ['compute', 'ec2']:
                categories['compute'] += cost
            elif service in ['storage', 's3', 'ebs']:
                categories['storage'] += cost
            elif service in ['networking', 'vpc', 'elb']:
                categories['networking'] += cost
            else:
                categories['other'] += cost
        
        result = []
        for category, cost in categories.items():
            if cost > 0:
                result.append({
                    'category': category.title(),
                    'cost': f"${cost:.2f}",
                    'percentage': f"{(cost / total * 100):.1f}%" if total > 0 else "0%"
                })
        
        return sorted(result, key=lambda x: float(x['cost'].replace('$', '')), reverse=True)
    
    async def _get_daily_spending_trend(self, billing_records, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get daily spending trend"""
        daily_costs = {}
        
        # Initialize all days with 0
        current = start_date
        while current <= end_date:
            daily_costs[current.strftime('%Y-%m-%d')] = Decimal('0')
            current += timedelta(days=1)
        
        # Add actual costs
        for record in billing_records:
            date = self._extract_date(record)
            cost = self._extract_cost(record)
            date_key = date.strftime('%Y-%m-%d')
            if date_key in daily_costs:
                daily_costs[date_key] += cost
        
        return [
            {
                'date': date,
                'cost': float(cost),
                'formatted_cost': f"${cost:.2f}",
                'day_of_week': datetime.strptime(date, '%Y-%m-%d').strftime('%a')
            }
            for date, cost in sorted(daily_costs.items())
        ]
    
    async def _get_quick_actions(self, user_id: str, cost_insights: List[CostInsight]) -> List[Dict[str, str]]:
        """Get quick action items"""
        actions = []
        
        # Easy wins from insights
        easy_insights = [i for i in cost_insights if i.difficulty == "easy"][:3]
        for insight in easy_insights:
            actions.append({
                'title': insight.title,
                'action': insight.action_steps[0] if insight.action_steps else "Review resource",
                'savings': f"${insight.potential_savings:.2f}",
                'time': insight.time_to_implement
            })
        
        # Default actions if no insights
        if not actions:
            actions.extend([
                {
                    'title': 'Review your highest-cost resources',
                    'action': 'Check your most expensive instances',
                    'savings': 'Varies',
                    'time': '5 minutes'
                },
                {
                    'title': 'Set up budget alerts',
                    'action': 'Configure spending notifications',
                    'savings': 'Prevention',
                    'time': '2 minutes'
                }
            ])
        
        return actions
    
    async def _get_helpful_tips(self, cost_summary: SimpleCostSummary, budget_alerts: List[BudgetAlert]) -> List[str]:
        """Get contextual helpful tips"""
        tips = []
        
        if cost_summary.cost_trend == "increasing":
            tips.append("💡 Rising costs? Check for new instances or increased usage patterns")
        
        if budget_alerts and budget_alerts[0].severity in [BudgetStatus.WARNING, BudgetStatus.CRITICAL]:
            tips.append("🎯 Set up automatic instance shutdown to avoid budget overruns")
        
        tips.extend([
            "📊 Review your daily spending patterns to identify unusual spikes",
            "⏰ Schedule non-production workloads to run during off-hours",
            "💰 Consider reserved instances for workloads running 24/7",
            "🔍 Use cost allocation tags to track spending by project or team"
        ])
        
        return tips[:4]  # Return top 4 tips
    
    def _get_status_color(self, status: BudgetStatus) -> str:
        """Get color for budget status"""
        colors = {
            BudgetStatus.HEALTHY: "green",
            BudgetStatus.WARNING: "yellow", 
            BudgetStatus.CRITICAL: "orange",
            BudgetStatus.OVER_BUDGET: "red"
        }
        return colors.get(status, "gray")
    
    def _calculate_budget_status(self, current_spend: Decimal, budget_limit: Decimal) -> BudgetStatus:
        """Calculate budget status"""
        percentage = (current_spend / budget_limit) * 100
        
        if percentage >= 100:
            return BudgetStatus.OVER_BUDGET
        elif percentage >= 90:
            return BudgetStatus.CRITICAL
        elif percentage >= 70:
            return BudgetStatus.WARNING
        else:
            return BudgetStatus.HEALTHY
    
    def _calculate_optimization_score(self, utilization_data) -> int:
        """Calculate optimization score (0-100)"""
        if not utilization_data:
            return 50
        
        avg_efficiency = sum(u.cost_efficiency_score for u in utilization_data) / len(utilization_data)
        underutilized = len([u for u in utilization_data if u.utilization_percent < 30])
        
        score = int(avg_efficiency)
        score -= (underutilized * 10)  # Penalty for underutilized resources
        
        return max(0, min(100, score))
    
    # Placeholder methods for future implementation
    async def _get_current_month_spend(self, user_id: str) -> Decimal:
        """Get current month spending"""
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        records = await self._get_billing_records(user_id, month_start, now)
        return sum(self._extract_cost(r) for r in records)
    
    async def _get_user_budgets(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user budgets (placeholder)"""
        # In real implementation, this would query a budgets table
        return []
    
    async def _create_default_budgets(self, user_id: str, current_spend: Decimal) -> List[Dict[str, Any]]:
        """Create default budgets based on current spend"""
        default_budget = max(current_spend * 2, Decimal('100'))  # 2x current or $100 minimum
        return [
            {
                'name': 'Monthly Budget',
                'limit': float(default_budget),
                'period': 'monthly'
            }
        ]
    
    async def _project_month_end_spend(self, user_id: str) -> str:
        """Project month-end spending"""
        current_spend = await self._get_current_month_spend(user_id)
        now = datetime.now()
        days_elapsed = now.day
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        
        daily_avg = current_spend / days_elapsed if days_elapsed > 0 else Decimal('0')
        projected = current_spend + (daily_avg * (days_in_month - days_elapsed))
        
        return f"${projected:.2f}"
    
    async def _calculate_spending_velocity(self, user_id: str) -> Dict[str, str]:
        """Calculate spending velocity"""
        current_spend = await self._get_current_month_spend(user_id)
        days_elapsed = datetime.now().day
        daily_avg = current_spend / days_elapsed if days_elapsed > 0 else Decimal('0')
        
        return {
            'daily_average': f"${daily_avg:.2f}",
            'weekly_projection': f"${daily_avg * 7:.2f}",
            'velocity_trend': 'stable'  # Simplified for now
        }
    
    async def _get_available_cost_controls(self, user_id: str) -> List[Dict[str, Any]]:
        """Get available cost control options"""
        return [
            {
                'name': 'Spending Alerts',
                'description': 'Get notified when you approach budget limits',
                'enabled': True
            },
            {
                'name': 'Auto Shutdown',
                'description': 'Automatically stop instances when budget is exceeded',
                'enabled': False
            },
            {
                'name': 'Approval Workflows',
                'description': 'Require approval for expensive resource launches',
                'enabled': False
            }
        ]
    
    async def _get_immediate_savings(self, user_id: str) -> List[Dict[str, str]]:
        """Get immediate savings opportunities"""
        return [
            {
                'opportunity': 'Stop idle instances',
                'potential_savings': '$50/month',
                'effort': 'Low'
            },
            {
                'opportunity': 'Right-size oversized instances',
                'potential_savings': '$75/month',
                'effort': 'Medium'
            }
        ]
    
    async def _get_budget_recommendations(self, status: BudgetStatus, current_spend: Decimal, budget_limit: Decimal) -> List[str]:
        """Get budget-specific recommendations"""
        recommendations = []
        
        if status == BudgetStatus.OVER_BUDGET:
            recommendations.extend([
                "Stop non-essential instances immediately",
                "Review and terminate unused resources",
                "Consider increasing your budget if needed"
            ])
        elif status == BudgetStatus.CRITICAL:
            recommendations.extend([
                "Monitor spending closely for remainder of month",
                "Defer non-urgent resource launches",
                "Review optimization opportunities"
            ])
        elif status == BudgetStatus.WARNING:
            recommendations.extend([
                "Set up daily spending alerts",
                "Review resource utilization",
                "Plan for potential budget adjustment"
            ])
        else:
            recommendations.extend([
                "Your spending is on track",
                "Continue monitoring trends",
                "Look for further optimization opportunities"
            ])
        
        return recommendations
    
    async def _get_payment_info(self, user_id: str) -> Dict[str, str]:
        """Get payment information (placeholder)"""
        return {
            'payment_method': 'Credit Card ending in 4242',
            'billing_address': 'On file',
            'next_billing_date': (datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1).strftime('%B %d, %Y'),
            'auto_pay': 'Enabled'
        }