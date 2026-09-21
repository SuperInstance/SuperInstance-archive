"""
Enhanced Billing Dashboard and User Experience
Provides comprehensive billing analytics, cost optimization, and user-friendly interfaces
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, field
from enum import Enum
import json
import statistics

from core.models import (
    User, BillingRecord, InstanceType, UserTier,
    current_timestamp, generate_id
)

class AlertType(str, Enum):
    BUDGET_WARNING = "budget_warning"
    BUDGET_EXCEEDED = "budget_exceeded"
    UNUSUAL_USAGE = "unusual_usage"
    COST_SPIKE = "cost_spike"
    OPTIMIZATION_OPPORTUNITY = "optimization_opportunity"
    PAYMENT_DUE = "payment_due"
    CREDIT_LOW = "credit_low"

class TimeRange(str, Enum):
    LAST_HOUR = "1h"
    LAST_24H = "24h"
    LAST_7D = "7d"
    LAST_30D = "30d"
    CURRENT_MONTH = "current_month"
    LAST_MONTH = "last_month"
    LAST_3M = "3m"
    LAST_6M = "6m"
    LAST_YEAR = "1y"

@dataclass
class BillingAlert:
    """Billing alert notification"""
    alert_id: str
    user_id: str
    alert_type: AlertType
    title: str
    message: str
    severity: str  # low, medium, high, critical
    threshold_value: Optional[float] = None
    current_value: Optional[float] = None
    suggested_action: Optional[str] = None
    created_at: datetime = field(default_factory=current_timestamp)
    acknowledged: bool = False

@dataclass
class UsageInsight:
    """Usage pattern insight"""
    insight_id: str
    user_id: str
    category: str  # cost_optimization, usage_pattern, efficiency
    title: str
    description: str
    impact: str  # low, medium, high
    potential_savings: Optional[float] = None
    recommendation: Optional[str] = None
    created_at: datetime = field(default_factory=current_timestamp)

@dataclass
class CostBreakdown:
    """Detailed cost breakdown"""
    period_start: datetime
    period_end: datetime
    total_cost: float
    by_service: Dict[str, float]
    by_instance_type: Dict[str, float]
    by_region: Dict[str, float]
    by_time_of_day: Dict[int, float]
    by_day_of_week: Dict[str, float]
    discounts_applied: Dict[str, float]
    taxes_and_fees: Dict[str, float]

class EnhancedBillingDashboard:
    """Enhanced billing dashboard with comprehensive analytics"""
    
    def __init__(self, config: Dict[str, Any], database_manager, billing_engine):
        self.config = config
        self.db = database_manager
        self.billing_engine = billing_engine
        self.logger = logging.getLogger(__name__)
        
        # Dashboard configuration
        self.currency = config.get('billing', {}).get('currency', 'USD')
        self.timezone = config.get('billing', {}).get('timezone', 'UTC')
        
        # Alert thresholds
        self.alert_thresholds = {
            'budget_warning': 0.80,  # 80% of budget
            'budget_critical': 0.95,  # 95% of budget
            'cost_spike_multiplier': 2.0,  # 2x normal usage
            'unusual_usage_std_dev': 2.0  # 2 standard deviations
        }
    
    async def get_billing_dashboard(self, user_id: str, time_range: TimeRange = TimeRange.CURRENT_MONTH) -> Dict[str, Any]:
        """Get comprehensive billing dashboard data"""
        try:
            # Get time period
            start_date, end_date = self._get_time_range_dates(time_range)
            
            # Get user information
            user = await self.db.get_user(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Get billing data
            billing_records = await self.db.get_billing_records(user_id, start_date, end_date)
            
            # Calculate dashboard metrics
            dashboard_data = {
                'user_info': {
                    'user_id': user_id,
                    'tier': user.tier.value,
                    'monthly_budget': user.monthly_budget,
                    'current_spend': user.current_spend,
                    'billing_status': user.billing_status.value
                },
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'time_range': time_range.value
                },
                'summary': await self._calculate_summary_metrics(billing_records, user),
                'cost_breakdown': await self._generate_cost_breakdown(billing_records, start_date, end_date),
                'usage_trends': await self._calculate_usage_trends(user_id, billing_records),
                'top_resources': await self._get_top_cost_resources(billing_records),
                'recent_activity': await self._get_recent_billing_activity(user_id, 10),
                'alerts': await self._get_active_alerts(user_id),
                'insights': await self._generate_usage_insights(user_id, billing_records),
                'projections': await self._calculate_projections(user_id, billing_records),
                'optimization': await self._get_optimization_suggestions(user_id, billing_records)
            }
            
            return dashboard_data
            
        except Exception as e:
            self.logger.error(f"Error generating billing dashboard for {user_id}: {e}")
            raise
    
    def _get_time_range_dates(self, time_range: TimeRange) -> Tuple[datetime, datetime]:
        """Convert time range enum to actual date range"""
        now = current_timestamp()
        
        if time_range == TimeRange.LAST_HOUR:
            start_date = now - timedelta(hours=1)
        elif time_range == TimeRange.LAST_24H:
            start_date = now - timedelta(hours=24)
        elif time_range == TimeRange.LAST_7D:
            start_date = now - timedelta(days=7)
        elif time_range == TimeRange.LAST_30D:
            start_date = now - timedelta(days=30)
        elif time_range == TimeRange.CURRENT_MONTH:
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif time_range == TimeRange.LAST_MONTH:
            # First day of last month
            first_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            start_date = (first_this_month - timedelta(days=1)).replace(day=1)
            now = first_this_month - timedelta(microseconds=1)
        elif time_range == TimeRange.LAST_3M:
            start_date = now - timedelta(days=90)
        elif time_range == TimeRange.LAST_6M:
            start_date = now - timedelta(days=180)
        elif time_range == TimeRange.LAST_YEAR:
            start_date = now - timedelta(days=365)
        else:
            start_date = now - timedelta(days=30)  # Default to 30 days
        
        return start_date, now
    
    async def _calculate_summary_metrics(self, billing_records: List[BillingRecord], user: User) -> Dict[str, Any]:
        """Calculate summary billing metrics"""
        if not billing_records:
            return {
                'total_cost': 0.0,
                'total_hours': 0.0,
                'average_hourly_cost': 0.0,
                'budget_utilization': 0.0,
                'cost_change_percent': 0.0,
                'instance_count': 0
            }
        
        total_cost = sum(record.total_cost for record in billing_records)
        total_minutes = sum(record.duration_minutes for record in billing_records)
        total_hours = total_minutes / 60
        
        # Calculate budget utilization
        budget_utilization = 0.0
        if user.monthly_budget:
            budget_utilization = (user.current_spend / user.monthly_budget) * 100
        
        # Calculate cost change (compare with previous period)
        cost_change_percent = await self._calculate_cost_change(user.user_id, len(billing_records))
        
        # Count unique instances
        unique_instances = len(set(record.instance_id for record in billing_records))
        
        return {
            'total_cost': round(total_cost, 4),
            'total_hours': round(total_hours, 2),
            'average_hourly_cost': round(total_cost / total_hours, 4) if total_hours > 0 else 0.0,
            'budget_utilization': round(budget_utilization, 1),
            'cost_change_percent': round(cost_change_percent, 1),
            'instance_count': unique_instances,
            'billing_records': len(billing_records)
        }
    
    async def _generate_cost_breakdown(self, billing_records: List[BillingRecord], 
                                     start_date: datetime, end_date: datetime) -> CostBreakdown:
        """Generate detailed cost breakdown"""
        if not billing_records:
            return CostBreakdown(
                period_start=start_date,
                period_end=end_date,
                total_cost=0.0,
                by_service={'compute': 0.0},
                by_instance_type={},
                by_region={'us-west-2': 0.0},
                by_time_of_day={},
                by_day_of_week={},
                discounts_applied={},
                taxes_and_fees={}
            )
        
        total_cost = sum(record.total_cost for record in billing_records)
        
        # Break down by instance type
        by_instance_type = {}
        for record in billing_records:
            inst_type = record.instance_type.value
            by_instance_type[inst_type] = by_instance_type.get(inst_type, 0.0) + record.total_cost
        
        # Break down by time of day (24 hour format)
        by_time_of_day = {hour: 0.0 for hour in range(24)}
        for record in billing_records:
            hour = record.start_time.hour
            by_time_of_day[hour] += record.total_cost
        
        # Break down by day of week
        by_day_of_week = {
            'Monday': 0.0, 'Tuesday': 0.0, 'Wednesday': 0.0, 'Thursday': 0.0,
            'Friday': 0.0, 'Saturday': 0.0, 'Sunday': 0.0
        }
        for record in billing_records:
            day_name = record.start_time.strftime('%A')
            by_day_of_week[day_name] += record.total_cost
        
        return CostBreakdown(
            period_start=start_date,
            period_end=end_date,
            total_cost=total_cost,
            by_service={'compute': total_cost * 0.92, 'storage': total_cost * 0.05, 'network': total_cost * 0.03},
            by_instance_type=by_instance_type,
            by_region={'us-west-2': total_cost},  # Single region for now
            by_time_of_day=by_time_of_day,
            by_day_of_week=by_day_of_week,
            discounts_applied={'volume_discount': 0.0, 'tier_discount': 0.0},
            taxes_and_fees={'tax': 0.0, 'fees': 0.0}
        )
    
    async def _calculate_usage_trends(self, user_id: str, billing_records: List[BillingRecord]) -> Dict[str, Any]:
        """Calculate usage trends and patterns"""
        if len(billing_records) < 2:
            return {'trend': 'insufficient_data', 'daily_costs': [], 'weekly_pattern': {}}
        
        # Daily cost aggregation
        daily_costs = {}
        for record in billing_records:
            day_key = record.start_time.strftime('%Y-%m-%d')
            daily_costs[day_key] = daily_costs.get(day_key, 0.0) + record.total_cost
        
        # Sort by date
        sorted_days = sorted(daily_costs.items())
        daily_values = [cost for _, cost in sorted_days]
        
        # Calculate trend
        if len(daily_values) > 1:
            recent_avg = statistics.mean(daily_values[-7:]) if len(daily_values) >= 7 else statistics.mean(daily_values[-3:])
            earlier_avg = statistics.mean(daily_values[:7]) if len(daily_values) >= 14 else statistics.mean(daily_values[:-3])
            
            if recent_avg > earlier_avg * 1.1:
                trend = 'increasing'
            elif recent_avg < earlier_avg * 0.9:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
        
        # Weekly pattern (Monday = 0, Sunday = 6)
        weekly_pattern = {}
        for record in billing_records:
            weekday = record.start_time.strftime('%A')
            weekly_pattern[weekday] = weekly_pattern.get(weekday, 0.0) + record.total_cost
        
        return {
            'trend': trend,
            'daily_costs': [{'date': date, 'cost': cost} for date, cost in sorted_days],
            'weekly_pattern': weekly_pattern,
            'peak_usage_day': max(weekly_pattern.items(), key=lambda x: x[1])[0] if weekly_pattern else None,
            'average_daily_cost': statistics.mean(daily_values) if daily_values else 0.0
        }
    
    async def _get_top_cost_resources(self, billing_records: List[BillingRecord], limit: int = 10) -> List[Dict[str, Any]]:
        """Get top cost-consuming resources"""
        if not billing_records:
            return []
        
        # Aggregate by instance
        instance_costs = {}
        for record in billing_records:
            instance_id = record.instance_id
            if instance_id not in instance_costs:
                instance_costs[instance_id] = {
                    'instance_id': instance_id,
                    'instance_type': record.instance_type.value,
                    'total_cost': 0.0,
                    'total_hours': 0.0,
                    'cost_per_hour': 0.0
                }
            
            instance_costs[instance_id]['total_cost'] += record.total_cost
            instance_costs[instance_id]['total_hours'] += record.duration_minutes / 60
        
        # Calculate cost per hour and sort
        for instance_data in instance_costs.values():
            if instance_data['total_hours'] > 0:
                instance_data['cost_per_hour'] = instance_data['total_cost'] / instance_data['total_hours']
        
        # Sort by total cost and return top resources
        top_resources = sorted(
            instance_costs.values(),
            key=lambda x: x['total_cost'],
            reverse=True
        )[:limit]
        
        return [
            {
                'instance_id': resource['instance_id'],
                'instance_type': resource['instance_type'],
                'total_cost': round(resource['total_cost'], 4),
                'total_hours': round(resource['total_hours'], 2),
                'cost_per_hour': round(resource['cost_per_hour'], 4),
                'percentage_of_total': round(
                    (resource['total_cost'] / sum(r['total_cost'] for r in instance_costs.values())) * 100, 1
                )
            }
            for resource in top_resources
        ]
    
    async def _get_recent_billing_activity(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent billing activity"""
        try:
            # Get recent billing records
            recent_records = await self.db.get_billing_records(
                user_id, 
                start_date=current_timestamp() - timedelta(days=7),
                end_date=current_timestamp()
            )
            
            # Sort by timestamp and limit
            recent_records.sort(key=lambda x: x.start_time, reverse=True)
            limited_records = recent_records[:limit]
            
            return [
                {
                    'record_id': record.record_id,
                    'instance_id': record.instance_id,
                    'instance_type': record.instance_type.value,
                    'cost': round(record.total_cost, 4),
                    'duration_minutes': record.duration_minutes,
                    'start_time': record.start_time.isoformat(),
                    'end_time': record.end_time.isoformat()
                }
                for record in limited_records
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting recent billing activity: {e}")
            return []
    
    async def _calculate_cost_change(self, user_id: str, current_period_days: int) -> float:
        """Calculate cost change percentage compared to previous period"""
        try:
            # Get current period end date
            current_end = current_timestamp()
            current_start = current_end - timedelta(days=current_period_days)
            
            # Get previous period
            previous_end = current_start
            previous_start = previous_end - timedelta(days=current_period_days)
            
            # Get billing data for both periods
            current_records = await self.db.get_billing_records(user_id, current_start, current_end)
            previous_records = await self.db.get_billing_records(user_id, previous_start, previous_end)
            
            current_cost = sum(record.total_cost for record in current_records)
            previous_cost = sum(record.total_cost for record in previous_records)
            
            if previous_cost > 0:
                return ((current_cost - previous_cost) / previous_cost) * 100
            else:
                return 0.0 if current_cost == 0 else 100.0
                
        except Exception as e:
            self.logger.error(f"Error calculating cost change: {e}")
            return 0.0
    
    async def _get_active_alerts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get active billing alerts for user"""
        try:
            alerts = []
            
            # Get user info
            user = await self.db.get_user(user_id)
            if not user:
                return alerts
            
            # Budget alerts
            if user.monthly_budget and user.current_spend:
                budget_utilization = user.current_spend / user.monthly_budget
                
                if budget_utilization >= 0.95:
                    alerts.append({
                        'alert_id': generate_id('alert'),
                        'type': AlertType.BUDGET_EXCEEDED.value,
                        'title': 'Budget Exceeded',
                        'message': f'Current spend (${user.current_spend:.2f}) exceeds budget (${user.monthly_budget:.2f})',
                        'severity': 'critical',
                        'current_value': user.current_spend,
                        'threshold_value': user.monthly_budget
                    })
                elif budget_utilization >= 0.80:
                    alerts.append({
                        'alert_id': generate_id('alert'),
                        'type': AlertType.BUDGET_WARNING.value,
                        'title': 'Budget Warning',
                        'message': f'You have used {budget_utilization*100:.1f}% of your monthly budget',
                        'severity': 'medium',
                        'current_value': user.current_spend,
                        'threshold_value': user.monthly_budget * 0.80
                    })
            
            # Cost spike detection
            cost_change = await self._calculate_cost_change(user_id, 7)
            if cost_change > 100:  # 100% increase
                alerts.append({
                    'alert_id': generate_id('alert'),
                    'type': AlertType.COST_SPIKE.value,
                    'title': 'Unusual Cost Increase',
                    'message': f'Your costs have increased by {cost_change:.1f}% compared to last week',
                    'severity': 'high',
                    'current_value': cost_change,
                    'threshold_value': 100.0
                })
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Error getting active alerts: {e}")
            return []
    
    async def _generate_usage_insights(self, user_id: str, billing_records: List[BillingRecord]) -> List[Dict[str, Any]]:
        """Generate usage insights and recommendations"""
        insights = []
        
        if not billing_records:
            return insights
        
        try:
            # Underutilized instances insight
            instance_usage = {}
            for record in billing_records:
                inst_id = record.instance_id
                inst_type = record.instance_type.value
                
                if inst_id not in instance_usage:
                    instance_usage[inst_id] = {
                        'instance_type': inst_type,
                        'total_cost': 0.0,
                        'total_hours': 0.0
                    }
                
                instance_usage[inst_id]['total_cost'] += record.total_cost
                instance_usage[inst_id]['total_hours'] += record.duration_minutes / 60
            
            # Find potentially underutilized instances
            for inst_id, usage in instance_usage.items():
                if usage['total_hours'] > 0:
                    hourly_cost = usage['total_cost'] / usage['total_hours']
                    
                    # If running expensive instances for short periods
                    if hourly_cost > 0.10 and usage['total_hours'] < 24:  # Less than 1 day
                        potential_savings = usage['total_cost'] * 0.30  # Estimated 30% savings
                        insights.append({
                            'insight_id': generate_id('insight'),
                            'category': 'cost_optimization',
                            'title': 'Short-Running Expensive Instance',
                            'description': f'Instance {inst_id} ({usage["instance_type"]}) ran for only {usage["total_hours"]:.1f} hours',
                            'impact': 'medium',
                            'potential_savings': potential_savings,
                            'recommendation': 'Consider using smaller instances or spot instances for short-term workloads'
                        })
            
            # Usage pattern insights
            total_cost = sum(record.total_cost for record in billing_records)
            
            # Weekend usage insight
            weekend_cost = sum(
                record.total_cost for record in billing_records
                if record.start_time.weekday() >= 5  # Saturday = 5, Sunday = 6
            )
            
            if weekend_cost > total_cost * 0.3:  # More than 30% weekend usage
                insights.append({
                    'insight_id': generate_id('insight'),
                    'category': 'usage_pattern',
                    'title': 'High Weekend Usage',
                    'description': f'${weekend_cost:.2f} ({(weekend_cost/total_cost)*100:.1f}%) spent on weekend usage',
                    'impact': 'low',
                    'recommendation': 'Consider scheduled shutdowns for development instances on weekends'
                })
            
            # Instance type optimization
            instance_type_costs = {}
            for record in billing_records:
                inst_type = record.instance_type.value
                instance_type_costs[inst_type] = instance_type_costs.get(inst_type, 0.0) + record.total_cost
            
            # Check for potential downsizing opportunities
            for inst_type, cost in instance_type_costs.items():
                if inst_type.startswith('c5.') and cost > total_cost * 0.5:  # Compute-optimized instances >50% of cost
                    insights.append({
                        'insight_id': generate_id('insight'),
                        'category': 'cost_optimization',
                        'title': 'Compute-Optimized Instance Usage',
                        'description': f'{inst_type} instances account for ${cost:.2f} of your costs',
                        'impact': 'medium',
                        'recommendation': 'Monitor CPU utilization to ensure you need compute-optimized instances'
                    })
            
            return insights[:5]  # Return top 5 insights
            
        except Exception as e:
            self.logger.error(f"Error generating usage insights: {e}")
            return insights
    
    async def _calculate_projections(self, user_id: str, billing_records: List[BillingRecord]) -> Dict[str, Any]:
        """Calculate cost projections and forecasts"""
        try:
            if not billing_records:
                return {'monthly_projection': 0.0, 'confidence': 'low'}
            
            # Calculate daily average for the period
            if billing_records:
                total_cost = sum(record.total_cost for record in billing_records)
                period_days = (billing_records[-1].end_time - billing_records[0].start_time).days
                period_days = max(period_days, 1)  # Avoid division by zero
                
                daily_average = total_cost / period_days
                monthly_projection = daily_average * 30
                
                # Simple confidence calculation based on data points
                confidence = 'high' if len(billing_records) > 100 else 'medium' if len(billing_records) > 20 else 'low'
                
                return {
                    'monthly_projection': round(monthly_projection, 2),
                    'daily_average': round(daily_average, 2),
                    'confidence': confidence,
                    'based_on_days': period_days
                }
            
            return {'monthly_projection': 0.0, 'confidence': 'low'}
            
        except Exception as e:
            self.logger.error(f"Error calculating projections: {e}")
            return {'monthly_projection': 0.0, 'confidence': 'low'}
    
    async def _get_optimization_suggestions(self, user_id: str, billing_records: List[BillingRecord]) -> List[Dict[str, Any]]:
        """Get cost optimization suggestions"""
        suggestions = []
        
        if not billing_records:
            return suggestions
        
        try:
            total_cost = sum(record.total_cost for record in billing_records)
            
            # Suggestion 1: Consider reserved instances for long-running workloads
            long_running_cost = 0.0
            instance_hours = {}
            
            for record in billing_records:
                inst_id = record.instance_id
                instance_hours[inst_id] = instance_hours.get(inst_id, 0) + record.duration_minutes / 60
            
            for inst_id, hours in instance_hours.items():
                if hours > 100:  # More than 100 hours
                    inst_records = [r for r in billing_records if r.instance_id == inst_id]
                    inst_cost = sum(r.total_cost for r in inst_records)
                    long_running_cost += inst_cost
            
            if long_running_cost > total_cost * 0.6:  # 60% of costs from long-running instances
                estimated_savings = long_running_cost * 0.30  # 30% savings with reserved instances
                suggestions.append({
                    'title': 'Consider Reserved Instances',
                    'description': f'${long_running_cost:.2f} spent on long-running instances',
                    'potential_savings': f'${estimated_savings:.2f}/month',
                    'action': 'Switch to reserved instances for 30% cost reduction',
                    'impact': 'high'
                })
            
            # Suggestion 2: Optimize instance sizing
            oversized_instances = []
            for record in billing_records:
                if record.instance_type.value in ['c5.2xlarge', 'c5.4xlarge', 'r5.2xlarge']:
                    oversized_instances.append(record)
            
            if oversized_instances:
                oversized_cost = sum(r.total_cost for r in oversized_instances)
                if oversized_cost > total_cost * 0.3:
                    suggestions.append({
                        'title': 'Right-size Large Instances',
                        'description': f'${oversized_cost:.2f} spent on XL/2XL instances',
                        'potential_savings': f'${oversized_cost * 0.4:.2f}/month',
                        'action': 'Monitor utilization and downsize if possible',
                        'impact': 'medium'
                    })
            
            # Suggestion 3: Use spot instances for flexible workloads
            if total_cost > 50:  # Only suggest for meaningful costs
                estimated_spot_savings = total_cost * 0.60  # 60% savings potential
                suggestions.append({
                    'title': 'Consider Spot Instances',
                    'description': 'Flexible workloads could use spot instances',
                    'potential_savings': f'${estimated_spot_savings:.2f}/month',
                    'action': 'Use spot instances for batch processing and development',
                    'impact': 'medium'
                })
            
            return suggestions[:3]  # Return top 3 suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating optimization suggestions: {e}")
            return suggestions
    
    async def create_billing_alert(self, user_id: str, alert_type: AlertType, 
                                 title: str, message: str, severity: str = 'medium',
                                 threshold_value: float = None, current_value: float = None) -> str:
        """Create a billing alert for a user"""
        try:
            alert = BillingAlert(
                alert_id=generate_id('alert'),
                user_id=user_id,
                alert_type=alert_type,
                title=title,
                message=message,
                severity=severity,
                threshold_value=threshold_value,
                current_value=current_value
            )
            
            # Save alert to database (would implement this method)
            # await self.db.create_billing_alert(alert)
            
            self.logger.info(f"Created billing alert for user {user_id}: {title}")
            return alert.alert_id
            
        except Exception as e:
            self.logger.error(f"Error creating billing alert: {e}")
            raise
    
    async def get_detailed_invoice(self, user_id: str, invoice_id: str) -> Dict[str, Any]:
        """Get detailed invoice with line items and breakdowns"""
        try:
            # This would typically retrieve from database
            # For now, generate a comprehensive invoice structure
            
            user = await self.db.get_user(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Get billing period (last month)
            now = current_timestamp()
            period_start = (now.replace(day=1) - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            period_end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(microseconds=1)
            
            billing_records = await self.db.get_billing_records(user_id, period_start, period_end)
            cost_breakdown = await self._generate_cost_breakdown(billing_records, period_start, period_end)
            
            # Generate detailed invoice
            invoice = {
                'invoice_id': invoice_id,
                'user_info': {
                    'user_id': user_id,
                    'email': user.email,
                    'tier': user.tier.value,
                    'billing_address': {
                        'company': 'Cloud Infrastructure User',
                        'email': user.email
                    }
                },
                'invoice_details': {
                    'invoice_number': f'INV-{invoice_id[-8:]}',
                    'invoice_date': now.isoformat(),
                    'due_date': (now + timedelta(days=30)).isoformat(),
                    'billing_period': {
                        'start': period_start.isoformat(),
                        'end': period_end.isoformat()
                    }
                },
                'line_items': self._generate_invoice_line_items(billing_records, cost_breakdown),
                'summary': {
                    'subtotal': cost_breakdown.total_cost,
                    'discounts': sum(cost_breakdown.discounts_applied.values()),
                    'taxes': sum(cost_breakdown.taxes_and_fees.values()),
                    'total': cost_breakdown.total_cost + sum(cost_breakdown.taxes_and_fees.values()) - sum(cost_breakdown.discounts_applied.values())
                },
                'payment_info': {
                    'currency': self.currency,
                    'payment_terms': 'Net 30',
                    'payment_methods': ['Credit Card', 'Bank Transfer', 'ACH']
                }
            }
            
            return invoice
            
        except Exception as e:
            self.logger.error(f"Error generating detailed invoice: {e}")
            raise
    
    def _generate_invoice_line_items(self, billing_records: List[BillingRecord], 
                                   cost_breakdown: CostBreakdown) -> List[Dict[str, Any]]:
        """Generate detailed line items for invoice"""
        line_items = []
        
        # Group by instance type
        for instance_type, cost in cost_breakdown.by_instance_type.items():
            # Count minutes for this instance type
            total_minutes = sum(
                record.duration_minutes for record in billing_records
                if record.instance_type.value == instance_type
            )
            
            # Get rate per minute
            instance_records = [r for r in billing_records if r.instance_type.value == instance_type]
            if instance_records:
                rate_per_minute = instance_records[0].cost_per_minute
                
                line_items.append({
                    'description': f'{instance_type} Instance Usage',
                    'quantity': total_minutes,
                    'unit': 'minutes',
                    'rate': rate_per_minute,
                    'amount': cost,
                    'period': f'{cost_breakdown.period_start.strftime("%Y-%m-%d")} - {cost_breakdown.period_end.strftime("%Y-%m-%d")}'
                })
        
        # Add service charges
        if cost_breakdown.by_service.get('storage', 0) > 0:
            line_items.append({
                'description': 'Storage Services',
                'quantity': 1,
                'unit': 'month',
                'rate': cost_breakdown.by_service['storage'],
                'amount': cost_breakdown.by_service['storage'],
                'period': f'{cost_breakdown.period_start.strftime("%Y-%m-%d")} - {cost_breakdown.period_end.strftime("%Y-%m-%d")}'
            })
        
        return line_items
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for billing dashboard"""
        try:
            return {
                'service': 'billing_dashboard',
                'healthy': True,
                'currency': self.currency,
                'timezone': self.timezone,
                'alert_thresholds': self.alert_thresholds,
                'timestamp': current_timestamp().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Billing dashboard health check failed: {e}")
            return {
                'service': 'billing_dashboard',
                'healthy': False,
                'error': str(e),
                'timestamp': current_timestamp().isoformat()
            }