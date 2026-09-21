#!/usr/bin/env python3
"""
Business Analytics System
Comprehensive business intelligence and analytics platform

Features:
- Real-time business metrics dashboard
- Financial performance analytics
- Customer behavior analysis
- Revenue forecasting and modeling
- Operational efficiency tracking
- Market trend analysis
- Competitive intelligence
- Growth metrics and KPI tracking
- Predictive analytics for business decisions
- Custom reporting and visualization
- Data export and API integration
- Automated insights and recommendations
- Performance benchmarking
- Risk assessment and monitoring
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

logger = logging.getLogger(__name__)

class MetricType(str, Enum):
    FINANCIAL = "financial"
    CUSTOMER = "customer"
    OPERATIONAL = "operational"
    MARKETING = "marketing"
    PRODUCT = "product"
    GROWTH = "growth"

class MetricCategory(str, Enum):
    REVENUE = "revenue"
    COSTS = "costs"
    PROFITABILITY = "profitability"
    CASH_FLOW = "cash_flow"
    CUSTOMER_ACQUISITION = "customer_acquisition"
    CUSTOMER_RETENTION = "customer_retention"
    CUSTOMER_SATISFACTION = "customer_satisfaction"
    OPERATIONAL_EFFICIENCY = "operational_efficiency"
    PRODUCTIVITY = "productivity"
    MARKET_SHARE = "market_share"
    GROWTH_RATE = "growth_rate"

class TimeFrame(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"

class TrendDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    STABLE = "stable"
    VOLATILE = "volatile"

class BusinessMetric(BaseModel):
    id: str
    business_id: str
    name: str
    description: str
    
    # Classification
    type: MetricType
    category: MetricCategory
    
    # Current value
    current_value: float
    previous_value: Optional[float] = None
    target_value: Optional[float] = None
    
    # Historical data
    historical_data: List[Dict[str, Any]] = []  # [{timestamp, value, context}]
    
    # Metadata
    unit: str = ""  # $, %, count, etc.
    calculation_method: str = ""
    data_sources: List[str] = []
    
    # Analysis
    trend_direction: TrendDirection = TrendDirection.STABLE
    trend_strength: float = 0.0  # 0-1
    volatility_score: float = 0.0
    
    # Status
    is_healthy: bool = True
    alert_threshold: Optional[float] = None
    is_tracking_target: bool = False
    
    created_at: datetime
    updated_at: datetime

class Dashboard(BaseModel):
    id: str
    business_id: str
    name: str
    description: str
    
    # Configuration
    layout: Dict[str, Any] = {}
    refresh_frequency: int = 300  # seconds
    
    # Widgets/Cards
    metric_cards: List[str] = []  # metric IDs
    chart_configs: List[Dict[str, Any]] = []
    
    # Access
    is_public: bool = False
    shared_with: List[str] = []
    
    created_at: datetime
    updated_at: datetime
    created_by: str

class AnalyticsReport(BaseModel):
    id: str
    business_id: str
    name: str
    description: str
    
    # Report configuration
    report_type: str  # executive_summary, financial, customer, operational
    time_period: Dict[str, datetime]  # start_date, end_date
    included_metrics: List[str] = []
    
    # Content
    executive_summary: str = ""
    key_insights: List[str] = []
    recommendations: List[str] = []
    
    # Data
    metric_summaries: Dict[str, Any] = {}
    trend_analysis: Dict[str, Any] = {}
    comparative_analysis: Dict[str, Any] = {}
    
    # Settings
    auto_generate: bool = False
    generation_frequency: str = "monthly"
    
    created_at: datetime
    updated_at: datetime
    generated_by: str

class Forecast(BaseModel):
    id: str
    business_id: str
    metric_id: str
    
    # Forecast details
    forecast_type: str  # linear, exponential, seasonal
    forecast_horizon: int  # months
    confidence_level: float = 0.95
    
    # Predictions
    forecasted_values: List[Dict[str, Any]] = []  # [{date, value, confidence_interval}]
    
    # Model performance
    model_accuracy: float = 0.0
    mean_absolute_error: float = 0.0
    
    # Assumptions
    assumptions: List[str] = []
    external_factors: List[str] = []
    
    created_at: datetime
    updated_at: datetime

class Alert(BaseModel):
    id: str
    business_id: str
    metric_id: str
    
    # Alert configuration
    condition: str  # above, below, changed_by
    threshold_value: float
    threshold_percentage: Optional[float] = None
    
    # Status
    is_active: bool = True
    is_triggered: bool = False
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    
    # Notification
    notification_channels: List[str] = []  # email, slack, webhook
    recipients: List[str] = []
    
    created_at: datetime
    updated_at: datetime

class BusinessAnalyticsManager:
    def __init__(self):
        self.metrics: Dict[str, BusinessMetric] = {}
        self.dashboards: Dict[str, Dashboard] = {}
        self.reports: Dict[str, AnalyticsReport] = {}
        self.forecasts: Dict[str, Forecast] = {}
        self.alerts: Dict[str, Alert] = {}
        
        # Analytics cache
        self.analytics_cache: Dict[str, Dict[str, Any]] = {}
        
        # Initialize default metrics
        self._initialize_default_metrics()
    
    def _initialize_default_metrics(self):
        """Initialize default business metrics"""
        default_metrics = [
            {
                "name": "Monthly Recurring Revenue",
                "description": "Predictable revenue generated monthly",
                "type": MetricType.FINANCIAL,
                "category": MetricCategory.REVENUE,
                "unit": "$",
                "target_value": 10000
            },
            {
                "name": "Customer Acquisition Cost",
                "description": "Cost to acquire a new customer",
                "type": MetricType.CUSTOMER,
                "category": MetricCategory.CUSTOMER_ACQUISITION,
                "unit": "$",
                "target_value": 100
            },
            {
                "name": "Customer Lifetime Value",
                "description": "Total revenue expected from a customer",
                "type": MetricType.CUSTOMER,
                "category": MetricCategory.CUSTOMER_RETENTION,
                "unit": "$",
                "target_value": 500
            },
            {
                "name": "Monthly Churn Rate",
                "description": "Percentage of customers lost monthly",
                "type": MetricType.CUSTOMER,
                "category": MetricCategory.CUSTOMER_RETENTION,
                "unit": "%",
                "target_value": 5.0
            },
            {
                "name": "Gross Profit Margin",
                "description": "Gross profit as percentage of revenue",
                "type": MetricType.FINANCIAL,
                "category": MetricCategory.PROFITABILITY,
                "unit": "%",
                "target_value": 60.0
            },
            {
                "name": "Monthly Active Users",
                "description": "Number of active users per month",
                "type": MetricType.PRODUCT,
                "category": MetricCategory.CUSTOMER_RETENTION,
                "unit": "users",
                "target_value": 1000
            }
        ]
        
        for metric_data in default_metrics:
            metric_id = str(uuid.uuid4())
            metric = BusinessMetric(
                id=metric_id,
                business_id="default",
                name=metric_data["name"],
                description=metric_data["description"],
                type=metric_data["type"],
                category=metric_data["category"],
                current_value=0.0,
                target_value=metric_data.get("target_value"),
                unit=metric_data["unit"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            self.metrics[metric_id] = metric
    
    async def create_metric(self, business_id: str, metric_data: Dict[str, Any]) -> BusinessMetric:
        """Create a new business metric"""
        metric_id = str(uuid.uuid4())
        
        metric = BusinessMetric(
            id=metric_id,
            business_id=business_id,
            name=metric_data["name"],
            description=metric_data.get("description", ""),
            type=MetricType(metric_data.get("type", "financial")),
            category=MetricCategory(metric_data.get("category", "revenue")),
            current_value=metric_data.get("current_value", 0.0),
            target_value=metric_data.get("target_value"),
            unit=metric_data.get("unit", ""),
            calculation_method=metric_data.get("calculation_method", ""),
            data_sources=metric_data.get("data_sources", []),
            alert_threshold=metric_data.get("alert_threshold"),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.metrics[metric_id] = metric
        return metric
    
    async def update_metric_value(
        self, 
        metric_id: str, 
        value: float, 
        context: Dict[str, Any] = {}
    ) -> bool:
        """Update metric value and analyze trends"""
        metric = self.metrics.get(metric_id)
        if not metric:
            return False
        
        # Store previous value
        metric.previous_value = metric.current_value
        metric.current_value = value
        metric.updated_at = datetime.now()
        
        # Add to historical data
        metric.historical_data.append({
            "timestamp": datetime.now().isoformat(),
            "value": value,
            "context": context
        })
        
        # Keep only last 100 data points
        if len(metric.historical_data) > 100:
            metric.historical_data = metric.historical_data[-100:]
        
        # Analyze trends
        await self._analyze_metric_trends(metric_id)
        
        # Check alerts
        await self._check_metric_alerts(metric_id)
        
        return True
    
    async def _analyze_metric_trends(self, metric_id: str):
        """Analyze trends for a metric"""
        metric = self.metrics.get(metric_id)
        if not metric or len(metric.historical_data) < 3:
            return
        
        # Get recent values for trend analysis
        recent_values = [float(d["value"]) for d in metric.historical_data[-10:]]
        
        # Calculate trend direction and strength
        if len(recent_values) >= 2:
            # Simple linear regression for trend
            n = len(recent_values)
            x_values = list(range(n))
            x_mean = statistics.mean(x_values)
            y_mean = statistics.mean(recent_values)
            
            # Calculate slope
            numerator = sum((x_values[i] - x_mean) * (recent_values[i] - y_mean) for i in range(n))
            denominator = sum((x - x_mean) ** 2 for x in x_values)
            
            if denominator > 0:
                slope = numerator / denominator
                
                # Determine trend direction
                if abs(slope) < 0.1:
                    metric.trend_direction = TrendDirection.STABLE
                elif slope > 0:
                    metric.trend_direction = TrendDirection.UP
                else:
                    metric.trend_direction = TrendDirection.DOWN
                
                # Trend strength (0-1)
                metric.trend_strength = min(abs(slope), 1.0)
        
        # Calculate volatility
        if len(recent_values) >= 5:
            volatility = statistics.stdev(recent_values) / statistics.mean(recent_values) if statistics.mean(recent_values) > 0 else 0
            metric.volatility_score = min(volatility, 1.0)
            
            # High volatility indicates unstable metric
            if volatility > 0.3:
                metric.trend_direction = TrendDirection.VOLATILE
        
        # Health check
        metric.is_healthy = await self._assess_metric_health(metric)
    
    async def _assess_metric_health(self, metric: BusinessMetric) -> bool:
        """Assess if metric is healthy based on various factors"""
        health_factors = []
        
        # Target achievement
        if metric.target_value is not None:
            if metric.category in [MetricCategory.COSTS, MetricCategory.CUSTOMER_ACQUISITION]:
                # Lower is better for costs
                target_achievement = (metric.target_value / metric.current_value) if metric.current_value > 0 else 0
            else:
                # Higher is better for most metrics
                target_achievement = (metric.current_value / metric.target_value) if metric.target_value > 0 else 0
            
            health_factors.append(min(target_achievement, 1.0))
        
        # Trend direction
        if metric.trend_direction == TrendDirection.UP:
            if metric.category in [MetricCategory.COSTS, MetricCategory.CUSTOMER_ACQUISITION]:
                health_factors.append(0.5)  # Up trend in costs is bad
            else:
                health_factors.append(1.0)  # Up trend in revenue/growth is good
        elif metric.trend_direction == TrendDirection.DOWN:
            if metric.category in [MetricCategory.COSTS, MetricCategory.CUSTOMER_ACQUISITION]:
                health_factors.append(1.0)  # Down trend in costs is good
            else:
                health_factors.append(0.5)  # Down trend in revenue/growth is bad
        elif metric.trend_direction == TrendDirection.VOLATILE:
            health_factors.append(0.3)  # Volatility is generally bad
        else:
            health_factors.append(0.7)  # Stable is generally okay
        
        # Volatility check
        if metric.volatility_score < 0.2:
            health_factors.append(1.0)  # Low volatility is good
        elif metric.volatility_score < 0.5:
            health_factors.append(0.7)
        else:
            health_factors.append(0.3)  # High volatility is concerning
        
        # Overall health score
        overall_health = statistics.mean(health_factors) if health_factors else 0.5
        return overall_health >= 0.6
    
    async def _check_metric_alerts(self, metric_id: str):
        """Check if any alerts should be triggered for this metric"""
        metric = self.metrics.get(metric_id)
        if not metric:
            return
        
        # Get alerts for this metric
        metric_alerts = [a for a in self.alerts.values() if a.metric_id == metric_id and a.is_active]
        
        for alert in metric_alerts:
            should_trigger = False
            
            if alert.condition == "above" and metric.current_value > alert.threshold_value:
                should_trigger = True
            elif alert.condition == "below" and metric.current_value < alert.threshold_value:
                should_trigger = True
            elif alert.condition == "changed_by" and metric.previous_value is not None:
                if alert.threshold_percentage:
                    change_percentage = abs((metric.current_value - metric.previous_value) / metric.previous_value) * 100
                    if change_percentage >= alert.threshold_percentage:
                        should_trigger = True
            
            if should_trigger and not alert.is_triggered:
                alert.is_triggered = True
                alert.last_triggered = datetime.now()
                alert.trigger_count += 1
                
                # In production, send actual notifications
                logger.info(f"Alert triggered for metric {metric.name}: {alert.condition} {alert.threshold_value}")
    
    async def create_dashboard(self, business_id: str, dashboard_data: Dict[str, Any]) -> Dashboard:
        """Create a new analytics dashboard"""
        dashboard_id = str(uuid.uuid4())
        
        dashboard = Dashboard(
            id=dashboard_id,
            business_id=business_id,
            name=dashboard_data["name"],
            description=dashboard_data.get("description", ""),
            layout=dashboard_data.get("layout", {}),
            refresh_frequency=dashboard_data.get("refresh_frequency", 300),
            metric_cards=dashboard_data.get("metric_cards", []),
            chart_configs=dashboard_data.get("chart_configs", []),
            is_public=dashboard_data.get("is_public", False),
            shared_with=dashboard_data.get("shared_with", []),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            created_by=dashboard_data.get("created_by", "user")
        )
        
        self.dashboards[dashboard_id] = dashboard
        return dashboard
    
    async def get_dashboard_data(self, dashboard_id: str) -> Dict[str, Any]:
        """Get dashboard data with current metric values"""
        dashboard = self.dashboards.get(dashboard_id)
        if not dashboard:
            return {}
        
        dashboard_data = {
            "dashboard": dashboard.dict(),
            "metrics": {},
            "charts": [],
            "last_updated": datetime.now().isoformat()
        }
        
        # Get current metric values
        for metric_id in dashboard.metric_cards:
            metric = self.metrics.get(metric_id)
            if metric:
                dashboard_data["metrics"][metric_id] = {
                    "name": metric.name,
                    "current_value": metric.current_value,
                    "previous_value": metric.previous_value,
                    "unit": metric.unit,
                    "trend_direction": metric.trend_direction,
                    "trend_strength": metric.trend_strength,
                    "is_healthy": metric.is_healthy,
                    "target_value": metric.target_value,
                    "target_progress": (metric.current_value / metric.target_value * 100) if metric.target_value else None
                }
        
        # Generate chart data
        for chart_config in dashboard.chart_configs:
            chart_data = await self._generate_chart_data(chart_config)
            dashboard_data["charts"].append(chart_data)
        
        return dashboard_data
    
    async def _generate_chart_data(self, chart_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate chart data based on configuration"""
        chart_type = chart_config.get("type", "line")
        metric_ids = chart_config.get("metrics", [])
        time_range = chart_config.get("time_range", 30)  # days
        
        chart_data = {
            "type": chart_type,
            "title": chart_config.get("title", "Chart"),
            "data": {"labels": [], "datasets": []}
        }
        
        if not metric_ids:
            return chart_data
        
        # Generate time labels
        end_date = datetime.now()
        start_date = end_date - timedelta(days=time_range)
        
        # For demo purposes, generate sample data points
        labels = []
        current_date = start_date
        while current_date <= end_date:
            labels.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=1)
        
        chart_data["data"]["labels"] = labels
        
        # Generate dataset for each metric
        for metric_id in metric_ids:
            metric = self.metrics.get(metric_id)
            if metric:
                # Generate sample historical data for visualization
                data_points = []
                base_value = metric.current_value if metric.current_value > 0 else 100
                
                for i, label in enumerate(labels):
                    # Add some realistic variation
                    variation = random.uniform(0.8, 1.2)
                    trend = 1 + (i * 0.01 * (1 if metric.trend_direction == TrendDirection.UP else -1 if metric.trend_direction == TrendDirection.DOWN else 0))
                    value = base_value * variation * trend
                    data_points.append(round(value, 2))
                
                dataset = {
                    "label": metric.name,
                    "data": data_points,
                    "borderColor": f"rgba({random.randint(0,255)}, {random.randint(0,255)}, {random.randint(0,255)}, 1)",
                    "backgroundColor": f"rgba({random.randint(0,255)}, {random.randint(0,255)}, {random.randint(0,255)}, 0.2)",
                    "tension": 0.1
                }
                chart_data["data"]["datasets"].append(dataset)
        
        return chart_data
    
    async def generate_forecast(self, metric_id: str, horizon_months: int = 6) -> Forecast:
        """Generate forecast for a metric"""
        metric = self.metrics.get(metric_id)
        if not metric:
            raise ValueError("Metric not found")
        
        forecast_id = str(uuid.uuid4())
        
        # Simple linear extrapolation for demo
        historical_values = [float(d["value"]) for d in metric.historical_data[-12:]]  # Last 12 points
        
        if len(historical_values) < 3:
            raise ValueError("Insufficient historical data for forecasting")
        
        # Calculate trend
        n = len(historical_values)
        x_values = list(range(n))
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(historical_values)
        
        numerator = sum((x_values[i] - x_mean) * (historical_values[i] - y_mean) for i in range(n))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        slope = numerator / denominator if denominator > 0 else 0
        intercept = y_mean - slope * x_mean
        
        # Generate forecasted values
        forecasted_values = []
        current_date = datetime.now()
        
        for i in range(horizon_months):
            forecast_date = current_date + timedelta(days=30 * (i + 1))  # Approximate monthly intervals
            x_value = n + i
            forecasted_value = slope * x_value + intercept
            
            # Add confidence interval (simplified)
            std_error = statistics.stdev(historical_values) * 0.1 * (i + 1)  # Increasing uncertainty
            
            forecasted_values.append({
                "date": forecast_date.isoformat(),
                "value": max(0, forecasted_value),  # Ensure non-negative
                "confidence_interval": {
                    "lower": max(0, forecasted_value - 1.96 * std_error),
                    "upper": forecasted_value + 1.96 * std_error
                }
            })
        
        # Calculate model accuracy (simplified)
        # In production, would use proper backtesting
        residuals = []
        for i in range(len(historical_values)):
            predicted = slope * i + intercept
            actual = historical_values[i]
            residuals.append(abs(actual - predicted))
        
        mean_absolute_error = statistics.mean(residuals) if residuals else 0
        model_accuracy = max(0, 1 - (mean_absolute_error / statistics.mean(historical_values))) if statistics.mean(historical_values) > 0 else 0
        
        forecast = Forecast(
            id=forecast_id,
            business_id=metric.business_id,
            metric_id=metric_id,
            forecast_type="linear",
            forecast_horizon=horizon_months,
            forecasted_values=forecasted_values,
            model_accuracy=model_accuracy,
            mean_absolute_error=mean_absolute_error,
            assumptions=[
                "Current trends continue",
                "No major market disruptions",
                "Seasonal patterns remain consistent"
            ],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.forecasts[forecast_id] = forecast
        return forecast
    
    async def generate_business_insights(self, business_id: str) -> Dict[str, Any]:
        """Generate AI-powered business insights"""
        business_metrics = [m for m in self.metrics.values() if m.business_id == business_id]
        
        if not business_metrics:
            return {"insights": [], "recommendations": []}
        
        insights = []
        recommendations = []
        
        # Analyze revenue metrics
        revenue_metrics = [m for m in business_metrics if m.category == MetricCategory.REVENUE]
        for metric in revenue_metrics:
            if metric.trend_direction == TrendDirection.UP:
                insights.append(f"Revenue metric '{metric.name}' showing positive growth trend (+{metric.trend_strength:.1%})")
            elif metric.trend_direction == TrendDirection.DOWN:
                insights.append(f"Revenue metric '{metric.name}' declining ({metric.trend_strength:.1%})")
                recommendations.append(f"Investigate causes of decline in {metric.name} and implement recovery plan")
        
        # Analyze customer metrics
        customer_metrics = [m for m in business_metrics if m.type == MetricType.CUSTOMER]
        for metric in customer_metrics:
            if metric.volatility_score > 0.4:
                insights.append(f"Customer metric '{metric.name}' showing high volatility")
                recommendations.append(f"Stabilize {metric.name} through improved processes or customer engagement")
        
        # Health assessment
        healthy_metrics = len([m for m in business_metrics if m.is_healthy])
        total_metrics = len(business_metrics)
        health_score = (healthy_metrics / total_metrics) * 100 if total_metrics > 0 else 0
        
        if health_score >= 80:
            insights.append(f"Overall business metrics health is excellent ({health_score:.0f}%)")
        elif health_score >= 60:
            insights.append(f"Business metrics health is good ({health_score:.0f}%)")
            recommendations.append("Focus on improving underperforming metrics for optimal growth")
        else:
            insights.append(f"Business metrics health needs attention ({health_score:.0f}%)")
            recommendations.append("Urgent review required for multiple underperforming metrics")
        
        # Target achievement analysis
        metrics_with_targets = [m for m in business_metrics if m.target_value is not None]
        if metrics_with_targets:
            achieving_targets = 0
            for metric in metrics_with_targets:
                if metric.category in [MetricCategory.COSTS, MetricCategory.CUSTOMER_ACQUISITION]:
                    # Lower is better
                    if metric.current_value <= metric.target_value:
                        achieving_targets += 1
                else:
                    # Higher is better
                    if metric.current_value >= metric.target_value:
                        achieving_targets += 1
            
            target_achievement_rate = (achieving_targets / len(metrics_with_targets)) * 100
            insights.append(f"Target achievement rate: {target_achievement_rate:.0f}% ({achieving_targets}/{len(metrics_with_targets)} metrics)")
            
            if target_achievement_rate < 50:
                recommendations.append("Review and adjust targets or improve performance to meet goals")
        
        return {
            "business_id": business_id,
            "insights": insights[:10],  # Top 10 insights
            "recommendations": recommendations[:8],  # Top 8 recommendations
            "overall_health_score": health_score,
            "metrics_analyzed": len(business_metrics),
            "generated_at": datetime.now().isoformat()
        }
    
    async def create_automated_report(self, business_id: str, report_config: Dict[str, Any]) -> AnalyticsReport:
        """Create automated analytics report"""
        report_id = str(uuid.uuid4())
        
        # Get time period
        end_date = datetime.now()
        start_date = end_date - timedelta(days=report_config.get("period_days", 30))
        
        # Get relevant metrics
        business_metrics = [m for m in self.metrics.values() if m.business_id == business_id]
        included_metrics = report_config.get("included_metrics", [m.id for m in business_metrics])
        
        # Generate executive summary
        insights = await self.generate_business_insights(business_id)
        executive_summary = f"""
        Business Performance Summary ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})
        
        Key Highlights:
        - {len(business_metrics)} metrics tracked
        - Overall health score: {insights['overall_health_score']:.0f}%
        - {len(insights['insights'])} key insights identified
        - {len(insights['recommendations'])} recommendations generated
        """
        
        # Generate metric summaries
        metric_summaries = {}
        for metric_id in included_metrics:
            metric = self.metrics.get(metric_id)
            if metric:
                metric_summaries[metric_id] = {
                    "name": metric.name,
                    "current_value": metric.current_value,
                    "previous_value": metric.previous_value,
                    "change": metric.current_value - metric.previous_value if metric.previous_value else 0,
                    "change_percentage": ((metric.current_value - metric.previous_value) / metric.previous_value * 100) if metric.previous_value and metric.previous_value != 0 else 0,
                    "trend": metric.trend_direction,
                    "health_status": "healthy" if metric.is_healthy else "needs_attention"
                }
        
        report = AnalyticsReport(
            id=report_id,
            business_id=business_id,
            name=report_config.get("name", "Business Analytics Report"),
            description=report_config.get("description", "Automated business performance report"),
            report_type=report_config.get("report_type", "executive_summary"),
            time_period={"start_date": start_date, "end_date": end_date},
            included_metrics=included_metrics,
            executive_summary=executive_summary,
            key_insights=insights["insights"],
            recommendations=insights["recommendations"],
            metric_summaries=metric_summaries,
            auto_generate=report_config.get("auto_generate", False),
            generation_frequency=report_config.get("generation_frequency", "monthly"),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            generated_by=report_config.get("generated_by", "system")
        )
        
        self.reports[report_id] = report
        return report
    
    async def get_kpi_dashboard(self, business_id: str) -> Dict[str, Any]:
        """Get key performance indicators dashboard"""
        business_metrics = [m for m in self.metrics.values() if m.business_id == business_id]
        
        # Categorize metrics
        kpi_categories = {}
        for category in MetricCategory:
            category_metrics = [m for m in business_metrics if m.category == category]
            if category_metrics:
                kpi_categories[category.value] = {
                    "metrics": [
                        {
                            "id": m.id,
                            "name": m.name,
                            "value": m.current_value,
                            "unit": m.unit,
                            "trend": m.trend_direction,
                            "health": m.is_healthy
                        } for m in category_metrics
                    ],
                    "health_score": (len([m for m in category_metrics if m.is_healthy]) / len(category_metrics)) * 100
                }
        
        # Calculate overall scores
        financial_health = kpi_categories.get("revenue", {}).get("health_score", 0)
        customer_health = sum([
            kpi_categories.get("customer_acquisition", {}).get("health_score", 0),
            kpi_categories.get("customer_retention", {}).get("health_score", 0),
            kpi_categories.get("customer_satisfaction", {}).get("health_score", 0)
        ]) / 3
        
        operational_health = kpi_categories.get("operational_efficiency", {}).get("health_score", 0)
        
        return {
            "business_id": business_id,
            "overview": {
                "total_metrics": len(business_metrics),
                "healthy_metrics": len([m for m in business_metrics if m.is_healthy]),
                "overall_health": (len([m for m in business_metrics if m.is_healthy]) / len(business_metrics)) * 100 if business_metrics else 0
            },
            "category_health": {
                "financial": financial_health,
                "customer": customer_health,
                "operational": operational_health
            },
            "categories": kpi_categories,
            "top_performers": sorted(business_metrics, key=lambda m: m.current_value if m.category not in [MetricCategory.COSTS] else -m.current_value, reverse=True)[:5],
            "needs_attention": [m for m in business_metrics if not m.is_healthy][:5],
            "last_updated": datetime.now().isoformat()
        }
    
    async def compare_periods(self, business_id: str, current_days: int = 30, previous_days: int = 30) -> Dict[str, Any]:
        """Compare business metrics between two periods"""
        business_metrics = [m for m in self.metrics.values() if m.business_id == business_id]
        
        comparison_results = {}
        
        for metric in business_metrics:
            if len(metric.historical_data) < 2:
                continue
            
            # Get current period data (simplified - would need actual time-based filtering)
            current_values = [float(d["value"]) for d in metric.historical_data[-current_days:] if d]
            previous_values = [float(d["value"]) for d in metric.historical_data[-(current_days + previous_days):-current_days] if d]
            
            if not current_values or not previous_values:
                continue
            
            current_avg = statistics.mean(current_values)
            previous_avg = statistics.mean(previous_values)
            
            change = current_avg - previous_avg
            change_percentage = (change / previous_avg * 100) if previous_avg != 0 else 0
            
            comparison_results[metric.id] = {
                "metric_name": metric.name,
                "current_period_avg": current_avg,
                "previous_period_avg": previous_avg,
                "absolute_change": change,
                "percentage_change": change_percentage,
                "trend_interpretation": "improved" if change > 0 and metric.category not in [MetricCategory.COSTS] else "declined" if change > 0 else "improved" if metric.category in [MetricCategory.COSTS] else "declined",
                "significance": "high" if abs(change_percentage) > 20 else "medium" if abs(change_percentage) > 10 else "low"
            }
        
        return {
            "business_id": business_id,
            "comparison_period": f"Current {current_days} days vs Previous {previous_days} days",
            "results": comparison_results,
            "summary": {
                "total_metrics_compared": len(comparison_results),
                "improved_metrics": len([r for r in comparison_results.values() if r["trend_interpretation"] == "improved"]),
                "declined_metrics": len([r for r in comparison_results.values() if r["trend_interpretation"] == "declined"]),
                "significant_changes": len([r for r in comparison_results.values() if r["significance"] == "high"])
            },
            "generated_at": datetime.now().isoformat()
        }

# Global instance
business_analytics_manager = BusinessAnalyticsManager()