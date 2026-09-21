import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from .config import settings
import logging

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RevenueMetricType(Enum):
    MONTHLY_REVENUE = "monthly_revenue"
    DAILY_REVENUE = "daily_revenue"
    CONVERSION_RATE = "conversion_rate"
    AVERAGE_ORDER_VALUE = "average_order_value"
    CUSTOMER_ACQUISITION_COST = "customer_acquisition_cost"
    LIFETIME_VALUE = "lifetime_value"
    CHURN_RATE = "churn_rate"

@dataclass
class RevenueAlert:
    alert_id: str
    metric_type: RevenueMetricType
    current_value: float
    target_value: float
    variance_percentage: float
    severity: AlertSeverity
    message: str
    timestamp: str
    recommendations: List[str]

@dataclass
class RevenueTarget:
    target_type: str
    target_value: float
    current_value: float
    achievement_percentage: float
    time_period: str
    days_remaining: int
    projected_final_value: float
    on_track: bool

class RevenueMonitor:
    def __init__(self, monthly_target: float = 1.0):
        self.monthly_target = monthly_target
        self.daily_target = monthly_target / 30
        self.targets = {
            'monthly': monthly_target,
            'quarterly': monthly_target * 3,
            'yearly': monthly_target * 12
        }
        self.revenue_data = {}
        self.alerts = []
        self.monitoring_active = False
        self.alert_thresholds = {
            'critical': 0.5,  # 50% below target
            'high': 0.25,     # 25% below target
            'medium': 0.15,   # 15% below target
            'low': 0.1        # 10% below target
        }
    
    async def start_monitoring(self):
        """Start revenue monitoring background tasks"""
        self.monitoring_active = True
        
        # Start monitoring tasks
        asyncio.create_task(self._monitor_revenue_targets())
        asyncio.create_task(self._monitor_daily_metrics())
        asyncio.create_task(self._generate_alerts())
        
        logger.info(f"Revenue monitoring started with ${self.monthly_target} monthly target")
    
    async def stop_monitoring(self):
        """Stop revenue monitoring"""
        self.monitoring_active = False
        logger.info("Revenue monitoring stopped")
    
    async def record_revenue(self, amount: float, source: str = "general") -> Dict:
        """Record a revenue transaction"""
        try:
            today = datetime.now().date().isoformat()
            
            if today not in self.revenue_data:
                self.revenue_data[today] = {
                    'total': 0.0,
                    'transactions': [],
                    'sources': {}
                }
            
            # Record transaction
            transaction = {
                'amount': amount,
                'source': source,
                'timestamp': datetime.now().isoformat()
            }
            
            self.revenue_data[today]['total'] += amount
            self.revenue_data[today]['transactions'].append(transaction)
            
            if source not in self.revenue_data[today]['sources']:
                self.revenue_data[today]['sources'][source] = 0.0
            self.revenue_data[today]['sources'][source] += amount
            
            # Check if this brings us closer to targets
            target_status = await self.get_target_status()
            
            return {
                'success': True,
                'amount': amount,
                'daily_total': self.revenue_data[today]['total'],
                'target_status': target_status
            }
        
        except Exception as e:
            logger.error(f"Error recording revenue: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_target_status(self) -> Dict[str, RevenueTarget]:
        """Get current status of all revenue targets"""
        today = datetime.now().date()
        
        # Calculate current month revenue
        month_start = today.replace(day=1)
        month_revenue = await self._get_revenue_for_period(month_start, today)
        
        # Calculate current quarter revenue
        quarter_start = datetime(today.year, ((today.month - 1) // 3) * 3 + 1, 1).date()
        quarter_revenue = await self._get_revenue_for_period(quarter_start, today)
        
        # Calculate current year revenue
        year_start = today.replace(month=1, day=1)
        year_revenue = await self._get_revenue_for_period(year_start, today)
        
        targets = {}
        
        # Monthly target
        days_in_month = (today.replace(month=today.month+1) - timedelta(days=1)).day if today.month < 12 else 31
        days_passed = today.day
        days_remaining = days_in_month - days_passed
        
        monthly_projection = month_revenue * (days_in_month / days_passed) if days_passed > 0 else 0
        
        targets['monthly'] = RevenueTarget(
            target_type='monthly',
            target_value=self.targets['monthly'],
            current_value=month_revenue,
            achievement_percentage=(month_revenue / self.targets['monthly']) * 100,
            time_period=f"{today.year}-{today.month:02d}",
            days_remaining=days_remaining,
            projected_final_value=monthly_projection,
            on_track=monthly_projection >= self.targets['monthly']
        )
        
        # Quarterly target
        quarter_end = (quarter_start + timedelta(days=90)).replace(day=1) - timedelta(days=1)
        quarter_days_total = (quarter_end - quarter_start).days + 1
        quarter_days_passed = (today - quarter_start).days + 1
        quarter_days_remaining = quarter_days_total - quarter_days_passed
        
        quarterly_projection = quarter_revenue * (quarter_days_total / quarter_days_passed) if quarter_days_passed > 0 else 0
        
        targets['quarterly'] = RevenueTarget(
            target_type='quarterly',
            target_value=self.targets['quarterly'],
            current_value=quarter_revenue,
            achievement_percentage=(quarter_revenue / self.targets['quarterly']) * 100,
            time_period=f"Q{((today.month - 1) // 3) + 1}-{today.year}",
            days_remaining=quarter_days_remaining,
            projected_final_value=quarterly_projection,
            on_track=quarterly_projection >= self.targets['quarterly']
        )
        
        # Yearly target
        year_end = today.replace(month=12, day=31)
        year_days_total = (year_end - year_start).days + 1
        year_days_passed = (today - year_start).days + 1
        year_days_remaining = year_days_total - year_days_passed
        
        yearly_projection = year_revenue * (year_days_total / year_days_passed) if year_days_passed > 0 else 0
        
        targets['yearly'] = RevenueTarget(
            target_type='yearly',
            target_value=self.targets['yearly'],
            current_value=year_revenue,
            achievement_percentage=(year_revenue / self.targets['yearly']) * 100,
            time_period=str(today.year),
            days_remaining=year_days_remaining,
            projected_final_value=yearly_projection,
            on_track=yearly_projection >= self.targets['yearly']
        )
        
        return targets
    
    async def get_revenue_analytics(self, period_days: int = 30) -> Dict:
        """Get comprehensive revenue analytics"""
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=period_days)
            
            # Get revenue data for period
            period_revenue = await self._get_revenue_for_period(start_date, end_date)
            daily_revenues = await self._get_daily_revenues(start_date, end_date)
            
            # Calculate trends
            if len(daily_revenues) > 1:
                trend_slope = np.polyfit(range(len(daily_revenues)), daily_revenues, 1)[0]
                trend_direction = 'increasing' if trend_slope > 0 else 'decreasing'
            else:
                trend_slope = 0
                trend_direction = 'stable'
            
            # Calculate statistics
            daily_avg = period_revenue / period_days if period_days > 0 else 0
            daily_revenues_array = np.array(daily_revenues) if daily_revenues else np.array([0])
            
            analytics = {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': period_days
                },
                'revenue_summary': {
                    'total_revenue': period_revenue,
                    'daily_average': daily_avg,
                    'highest_day': float(np.max(daily_revenues_array)),
                    'lowest_day': float(np.min(daily_revenues_array)),
                    'standard_deviation': float(np.std(daily_revenues_array))
                },
                'trends': {
                    'direction': trend_direction,
                    'slope': float(trend_slope),
                    'growth_rate': float(trend_slope / max(daily_avg, 0.01)) if daily_avg > 0 else 0
                },
                'target_comparison': {
                    'daily_target': self.daily_target,
                    'target_achievement_rate': (daily_avg / self.daily_target) * 100 if self.daily_target > 0 else 0,
                    'days_above_target': len([r for r in daily_revenues if r >= self.daily_target]),
                    'days_below_target': len([r for r in daily_revenues if r < self.daily_target])
                }
            }
            
            return {
                'success': True,
                'analytics': analytics
            }
        
        except Exception as e:
            logger.error(f"Error getting revenue analytics: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_active_alerts(self) -> List[RevenueAlert]:
        """Get all active revenue alerts"""
        # Filter alerts from last 24 hours
        yesterday = datetime.now() - timedelta(days=1)
        
        active_alerts = [
            alert for alert in self.alerts
            if datetime.fromisoformat(alert.timestamp) >= yesterday
        ]
        
        return active_alerts
    
    async def set_revenue_targets(self, targets: Dict) -> Dict:
        """Update revenue targets"""
        try:
            if 'monthly' in targets:
                self.monthly_target = targets['monthly']
                self.daily_target = targets['monthly'] / 30
                self.targets['monthly'] = targets['monthly']
                self.targets['quarterly'] = targets['monthly'] * 3
                self.targets['yearly'] = targets['monthly'] * 12
            
            if 'quarterly' in targets:
                self.targets['quarterly'] = targets['quarterly']
            
            if 'yearly' in targets:
                self.targets['yearly'] = targets['yearly']
            
            logger.info(f"Revenue targets updated: {self.targets}")
            
            return {
                'success': True,
                'new_targets': self.targets
            }
        
        except Exception as e:
            logger.error(f"Error setting revenue targets: {e}")
            return {'success': False, 'error': str(e)}
    
    async def generate_revenue_forecast(self, forecast_days: int = 30) -> Dict:
        """Generate revenue forecast based on historical data"""
        try:
            # Get historical data
            historical_days = min(90, len(self.revenue_data))
            if historical_days < 7:
                return {
                    'success': False,
                    'error': 'Insufficient historical data for forecasting'
                }
            
            # Get recent daily revenues
            recent_dates = sorted(self.revenue_data.keys())[-historical_days:]
            recent_revenues = [self.revenue_data[date]['total'] for date in recent_dates]
            
            # Simple linear trend forecast
            x = np.arange(len(recent_revenues))
            coefficients = np.polyfit(x, recent_revenues, 1)
            trend_slope, trend_intercept = coefficients
            
            # Generate forecast
            forecast_start = len(recent_revenues)
            forecast_x = np.arange(forecast_start, forecast_start + forecast_days)
            forecast_values = trend_slope * forecast_x + trend_intercept
            
            # Add some realistic variability
            noise = np.random.normal(0, np.std(recent_revenues) * 0.1, forecast_days)
            forecast_values_adjusted = np.maximum(0, forecast_values + noise)
            
            forecast_dates = []
            last_date = datetime.now().date()
            for i in range(forecast_days):
                forecast_date = last_date + timedelta(days=i+1)
                forecast_dates.append(forecast_date.isoformat())
            
            total_forecasted = float(np.sum(forecast_values_adjusted))
            
            return {
                'success': True,
                'forecast_period_days': forecast_days,
                'historical_data_points': len(recent_revenues),
                'trend_slope': float(trend_slope),
                'daily_forecast': [
                    {
                        'date': date,
                        'forecasted_revenue': float(value)
                    }
                    for date, value in zip(forecast_dates, forecast_values_adjusted)
                ],
                'total_forecasted_revenue': total_forecasted,
                'average_daily_forecast': total_forecasted / forecast_days,
                'confidence_level': min(0.9, historical_days / 90)  # Higher confidence with more data
            }
        
        except Exception as e:
            logger.error(f"Error generating revenue forecast: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _monitor_revenue_targets(self):
        """Background task to monitor revenue targets"""
        while self.monitoring_active:
            try:
                target_status = await self.get_target_status()
                
                for target_type, target in target_status.items():
                    if not target.on_track:
                        variance = ((target.target_value - target.projected_final_value) / target.target_value) * 100
                        
                        # Determine alert severity
                        severity = self._determine_alert_severity(variance)
                        
                        if severity:
                            alert = await self._create_target_alert(target, variance, severity)
                            self.alerts.append(alert)
                
                await asyncio.sleep(3600)  # Check every hour
            
            except Exception as e:
                logger.error(f"Error in revenue target monitoring: {e}")
                await asyncio.sleep(3600)
    
    async def _monitor_daily_metrics(self):
        """Background task to monitor daily revenue metrics"""
        while self.monitoring_active:
            try:
                today = datetime.now().date().isoformat()
                today_revenue = self.revenue_data.get(today, {}).get('total', 0.0)
                
                # Check if today's revenue is significantly below target
                if today_revenue < self.daily_target * 0.5:  # 50% below daily target
                    alert = await self._create_daily_alert(today_revenue)
                    self.alerts.append(alert)
                
                await asyncio.sleep(1800)  # Check every 30 minutes
            
            except Exception as e:
                logger.error(f"Error in daily metrics monitoring: {e}")
                await asyncio.sleep(1800)
    
    async def _generate_alerts(self):
        """Background task to generate and clean up alerts"""
        while self.monitoring_active:
            try:
                # Clean up old alerts (older than 7 days)
                cutoff_date = datetime.now() - timedelta(days=7)
                self.alerts = [
                    alert for alert in self.alerts
                    if datetime.fromisoformat(alert.timestamp) >= cutoff_date
                ]
                
                await asyncio.sleep(3600)  # Clean up every hour
            
            except Exception as e:
                logger.error(f"Error in alert generation: {e}")
                await asyncio.sleep(3600)
    
    async def _get_revenue_for_period(self, start_date, end_date) -> float:
        """Get total revenue for a specific period"""
        total_revenue = 0.0
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.isoformat()
            if date_str in self.revenue_data:
                total_revenue += self.revenue_data[date_str]['total']
            current_date += timedelta(days=1)
        
        return total_revenue
    
    async def _get_daily_revenues(self, start_date, end_date) -> List[float]:
        """Get daily revenue values for a period"""
        daily_revenues = []
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.isoformat()
            revenue = self.revenue_data.get(date_str, {}).get('total', 0.0)
            daily_revenues.append(revenue)
            current_date += timedelta(days=1)
        
        return daily_revenues
    
    def _determine_alert_severity(self, variance_percentage: float) -> Optional[AlertSeverity]:
        """Determine alert severity based on variance from target"""
        abs_variance = abs(variance_percentage)
        
        if abs_variance >= self.alert_thresholds['critical'] * 100:
            return AlertSeverity.CRITICAL
        elif abs_variance >= self.alert_thresholds['high'] * 100:
            return AlertSeverity.HIGH
        elif abs_variance >= self.alert_thresholds['medium'] * 100:
            return AlertSeverity.MEDIUM
        elif abs_variance >= self.alert_thresholds['low'] * 100:
            return AlertSeverity.LOW
        
        return None
    
    async def _create_target_alert(self, target: RevenueTarget, variance: float, severity: AlertSeverity) -> RevenueAlert:
        """Create an alert for target deviation"""
        recommendations = []
        
        if target.target_type == 'monthly':
            if variance > 25:
                recommendations.extend([
                    "Review and optimize marketing campaigns",
                    "Implement upselling strategies for existing customers",
                    "Analyze and address conversion funnel bottlenecks"
                ])
            else:
                recommendations.extend([
                    "Monitor daily performance more closely",
                    "Consider promotional campaigns for month-end push"
                ])
        
        alert_id = f"target_{target.target_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return RevenueAlert(
            alert_id=alert_id,
            metric_type=RevenueMetricType.MONTHLY_REVENUE,
            current_value=target.projected_final_value,
            target_value=target.target_value,
            variance_percentage=variance,
            severity=severity,
            message=f"{target.target_type.title()} revenue target at risk: {variance:.1f}% below target",
            timestamp=datetime.now().isoformat(),
            recommendations=recommendations
        )
    
    async def _create_daily_alert(self, today_revenue: float) -> RevenueAlert:
        """Create an alert for low daily revenue"""
        variance = ((self.daily_target - today_revenue) / self.daily_target) * 100
        
        recommendations = [
            "Review today's marketing performance",
            "Check for technical issues affecting conversions",
            "Consider immediate promotional activities",
            "Analyze traffic and conversion rates"
        ]
        
        alert_id = f"daily_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return RevenueAlert(
            alert_id=alert_id,
            metric_type=RevenueMetricType.DAILY_REVENUE,
            current_value=today_revenue,
            target_value=self.daily_target,
            variance_percentage=variance,
            severity=AlertSeverity.HIGH,
            message=f"Daily revenue significantly below target: ${today_revenue:.2f} vs ${self.daily_target:.2f}",
            timestamp=datetime.now().isoformat(),
            recommendations=recommendations
        )