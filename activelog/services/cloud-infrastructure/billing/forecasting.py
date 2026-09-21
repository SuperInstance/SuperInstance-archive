#!/usr/bin/env python3
"""
Usage Forecasting and Budget Planning System
Provides predictive analytics and budget planning capabilities.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import logging
import math

logger = logging.getLogger(__name__)

class ForecastModel(Enum):
    """Forecasting model types"""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    SEASONAL = "seasonal"
    ML_BASED = "ml_based"

class BudgetAlertLevel(Enum):
    """Budget alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class UsageForecast:
    """Usage forecast result"""
    forecast_id: str
    user_id: str
    org_id: Optional[str]
    forecast_period_days: int
    model_used: ForecastModel
    predicted_usage: Dict[str, Decimal] = field(default_factory=dict)
    predicted_cost: Decimal = Decimal('0.00')
    confidence_level: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    factors_considered: List[str] = field(default_factory=list)
    recommendations: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class BudgetPlan:
    """Budget planning information"""
    budget_id: str
    user_id: str
    org_id: Optional[str]
    name: str
    total_budget: Decimal
    monthly_budget: Decimal
    period_start: datetime
    period_end: datetime
    service_allocations: Dict[str, Decimal] = field(default_factory=dict)
    alert_thresholds: Dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    current_spend: Decimal = Decimal('0.00')
    projected_spend: Decimal = Decimal('0.00')
    status: str = "active"

@dataclass
class BudgetAlert:
    """Budget alert information"""
    alert_id: str
    budget_id: str
    user_id: str
    level: BudgetAlertLevel
    message: str
    percentage_used: float
    amount_over_budget: Decimal = Decimal('0.00')
    triggered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False

class UsageForecaster:
    """Usage forecasting and budget planning system"""
    
    def __init__(self, database_manager, billing_engine):
        self.database_manager = database_manager
        self.billing_engine = billing_engine
        
    async def initialize(self):
        """Initialize forecasting system"""
        await self._setup_forecasting_tables()
        
    async def _setup_forecasting_tables(self):
        """Setup forecasting-related database tables"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            # Usage forecasts table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS usage_forecasts (
                    forecast_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    org_id TEXT,
                    forecast_period_days INTEGER NOT NULL,
                    model_used TEXT NOT NULL,
                    predicted_usage TEXT,
                    predicted_cost DECIMAL(10,4) NOT NULL,
                    confidence_level REAL NOT NULL,
                    factors_considered TEXT,
                    recommendations TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Budget plans table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS budget_plans (
                    budget_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    org_id TEXT,
                    name TEXT NOT NULL,
                    total_budget DECIMAL(10,4) NOT NULL,
                    monthly_budget DECIMAL(10,4) NOT NULL,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    service_allocations TEXT,
                    alert_thresholds TEXT,
                    current_spend DECIMAL(10,4) DEFAULT 0.00,
                    projected_spend DECIMAL(10,4) DEFAULT 0.00,
                    status TEXT DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Budget alerts table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS budget_alerts (
                    alert_id TEXT PRIMARY KEY,
                    budget_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    percentage_used REAL NOT NULL,
                    amount_over_budget DECIMAL(10,4) DEFAULT 0.00,
                    triggered_at TEXT NOT NULL,
                    acknowledged BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (budget_id) REFERENCES budget_plans (budget_id),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            await conn.commit()
    
    # Usage Forecasting
    async def generate_usage_forecast(self, user_id: str, forecast_days: int = 30,
                                    model: ForecastModel = ForecastModel.LINEAR,
                                    org_id: Optional[str] = None) -> UsageForecast:
        """Generate usage forecast for a user"""
        forecast_id = f"forecast_{uuid.uuid4().hex[:12]}"
        
        # Get historical usage data
        historical_data = await self._get_historical_usage(user_id, days=90)
        
        if not historical_data:
            # No historical data, create basic forecast
            return UsageForecast(
                forecast_id=forecast_id,
                user_id=user_id,
                org_id=org_id,
                forecast_period_days=forecast_days,
                model_used=model,
                predicted_cost=Decimal('100.00'),  # Default baseline
                confidence_level=0.3,
                factors_considered=["no_historical_data"],
                recommendations=[{
                    "type": "baseline",
                    "message": "Start with a conservative budget as no historical data available",
                    "priority": "high"
                }]
            )
        
        # Apply forecasting model
        if model == ForecastModel.LINEAR:
            forecast = await self._linear_forecast(historical_data, forecast_days)
        elif model == ForecastModel.EXPONENTIAL:
            forecast = await self._exponential_forecast(historical_data, forecast_days)
        elif model == ForecastModel.SEASONAL:
            forecast = await self._seasonal_forecast(historical_data, forecast_days)
        else:  # ML_BASED
            forecast = await self._ml_based_forecast(historical_data, forecast_days)
        
        # Create forecast object
        usage_forecast = UsageForecast(
            forecast_id=forecast_id,
            user_id=user_id,
            org_id=org_id,
            forecast_period_days=forecast_days,
            model_used=model,
            predicted_usage=forecast['usage'],
            predicted_cost=forecast['cost'],
            confidence_level=forecast['confidence'],
            factors_considered=forecast['factors'],
            recommendations=forecast['recommendations']
        )
        
        # Store forecast
        await self._store_forecast(usage_forecast)
        
        logger.info(f"Generated {model.value} forecast {forecast_id} for user {user_id}: ${forecast['cost']} over {forecast_days} days")
        
        return usage_forecast
    
    async def _get_historical_usage(self, user_id: str, days: int = 90) -> List[Dict[str, Any]]:
        """Get historical usage data for forecasting"""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            async with conn.execute("""
                SELECT DATE(created_at) as usage_date, 
                       SUM(compute_cost) as daily_compute_cost,
                       SUM(storage_cost) as daily_storage_cost,
                       SUM(network_cost) as daily_network_cost,
                       SUM(total_cost) as daily_total_cost,
                       AVG(instance_count) as avg_instances
                FROM usage_records 
                WHERE user_id = ? AND created_at BETWEEN ? AND ?
                GROUP BY DATE(created_at)
                ORDER BY usage_date
            """, (user_id, start_date.isoformat(), end_date.isoformat())) as cursor:
                data = []
                async for row in cursor:
                    data.append({
                        'date': row[0],
                        'compute_cost': float(row[1] or 0),
                        'storage_cost': float(row[2] or 0),
                        'network_cost': float(row[3] or 0),
                        'total_cost': float(row[4] or 0),
                        'avg_instances': int(row[5] or 0)
                    })
                return data
    
    async def _linear_forecast(self, historical_data: List[Dict[str, Any]], 
                             forecast_days: int) -> Dict[str, Any]:
        """Linear trend forecasting"""
        if len(historical_data) < 7:
            return self._fallback_forecast(forecast_days)
        
        # Calculate linear trend for total cost
        daily_costs = [d['total_cost'] for d in historical_data[-30:]]  # Last 30 days
        avg_daily_cost = sum(daily_costs) / len(daily_costs)
        
        # Simple linear trend calculation
        if len(daily_costs) >= 2:
            trend = (daily_costs[-1] - daily_costs[0]) / len(daily_costs)
        else:
            trend = 0
        
        # Project forward
        predicted_daily_cost = max(0, avg_daily_cost + (trend * forecast_days / 2))
        predicted_total_cost = predicted_daily_cost * forecast_days
        
        # Calculate confidence based on data consistency
        cost_variance = sum((c - avg_daily_cost) ** 2 for c in daily_costs) / len(daily_costs)
        confidence = max(0.4, min(0.9, 1.0 - (cost_variance / (avg_daily_cost ** 2))))
        
        return {
            'usage': {
                'daily_compute_cost': Decimal(str(predicted_daily_cost * 0.6)),
                'daily_storage_cost': Decimal(str(predicted_daily_cost * 0.3)),
                'daily_network_cost': Decimal(str(predicted_daily_cost * 0.1))
            },
            'cost': Decimal(str(predicted_total_cost)),
            'confidence': confidence,
            'factors': ['historical_trend', 'linear_projection'],
            'recommendations': self._generate_forecast_recommendations(
                predicted_total_cost, avg_daily_cost, trend
            )
        }
    
    async def _exponential_forecast(self, historical_data: List[Dict[str, Any]], 
                                  forecast_days: int) -> Dict[str, Any]:
        """Exponential growth forecasting"""
        if len(historical_data) < 14:
            return await self._linear_forecast(historical_data, forecast_days)
        
        daily_costs = [d['total_cost'] for d in historical_data[-30:]]
        
        # Calculate exponential growth rate
        if daily_costs[0] > 0:
            growth_rate = (daily_costs[-1] / daily_costs[0]) ** (1 / len(daily_costs)) - 1
        else:
            growth_rate = 0.05  # 5% default growth
        
        # Cap extreme growth rates
        growth_rate = max(-0.1, min(0.2, growth_rate))  # Between -10% and +20%
        
        # Project exponential growth
        current_cost = daily_costs[-1]
        predicted_total_cost = sum(
            current_cost * ((1 + growth_rate) ** day) 
            for day in range(1, forecast_days + 1)
        )
        
        confidence = 0.7 if abs(growth_rate) < 0.05 else 0.5
        
        return {
            'usage': {
                'daily_compute_cost': Decimal(str(predicted_total_cost * 0.6 / forecast_days)),
                'daily_storage_cost': Decimal(str(predicted_total_cost * 0.3 / forecast_days)),
                'daily_network_cost': Decimal(str(predicted_total_cost * 0.1 / forecast_days))
            },
            'cost': Decimal(str(predicted_total_cost)),
            'confidence': confidence,
            'factors': ['exponential_growth', 'compound_scaling'],
            'recommendations': self._generate_forecast_recommendations(
                predicted_total_cost, current_cost, growth_rate
            )
        }
    
    async def _seasonal_forecast(self, historical_data: List[Dict[str, Any]], 
                               forecast_days: int) -> Dict[str, Any]:
        """Seasonal pattern forecasting"""
        if len(historical_data) < 21:
            return await self._linear_forecast(historical_data, forecast_days)
        
        # Detect weekly patterns
        daily_costs = [d['total_cost'] for d in historical_data[-42:]]  # 6 weeks
        
        # Calculate day-of-week averages
        weekly_pattern = {}
        for i, cost in enumerate(daily_costs):
            day_of_week = i % 7
            if day_of_week not in weekly_pattern:
                weekly_pattern[day_of_week] = []
            weekly_pattern[day_of_week].append(cost)
        
        # Average by day of week
        weekly_averages = {
            day: sum(costs) / len(costs) 
            for day, costs in weekly_pattern.items()
        }
        
        # Project using weekly pattern
        predicted_total_cost = 0
        base_cost = sum(weekly_averages.values()) / 7
        
        for day in range(forecast_days):
            day_of_week = day % 7
            day_multiplier = weekly_averages.get(day_of_week, base_cost) / base_cost
            predicted_total_cost += base_cost * day_multiplier
        
        return {
            'usage': {
                'daily_compute_cost': Decimal(str(predicted_total_cost * 0.6 / forecast_days)),
                'daily_storage_cost': Decimal(str(predicted_total_cost * 0.3 / forecast_days)),
                'daily_network_cost': Decimal(str(predicted_total_cost * 0.1 / forecast_days))
            },
            'cost': Decimal(str(predicted_total_cost)),
            'confidence': 0.8,
            'factors': ['weekly_patterns', 'seasonal_cycles'],
            'recommendations': self._generate_seasonal_recommendations(weekly_averages)
        }
    
    async def _ml_based_forecast(self, historical_data: List[Dict[str, Any]], 
                               forecast_days: int) -> Dict[str, Any]:
        """Machine learning based forecasting (simplified)"""
        # For demo purposes, this combines multiple approaches
        linear_forecast = await self._linear_forecast(historical_data, forecast_days)
        exponential_forecast = await self._exponential_forecast(historical_data, forecast_days)
        seasonal_forecast = await self._seasonal_forecast(historical_data, forecast_days)
        
        # Weighted ensemble
        predicted_cost = (
            linear_forecast['cost'] * Decimal('0.4') +
            exponential_forecast['cost'] * Decimal('0.3') +
            seasonal_forecast['cost'] * Decimal('0.3')
        )
        
        return {
            'usage': {
                'daily_compute_cost': Decimal(str(predicted_cost * Decimal('0.6') / forecast_days)),
                'daily_storage_cost': Decimal(str(predicted_cost * Decimal('0.3') / forecast_days)),
                'daily_network_cost': Decimal(str(predicted_cost * Decimal('0.1') / forecast_days))
            },
            'cost': predicted_cost,
            'confidence': 0.85,
            'factors': ['ensemble_model', 'multiple_algorithms', 'historical_patterns'],
            'recommendations': self._generate_ml_recommendations(
                linear_forecast, exponential_forecast, seasonal_forecast
            )
        }
    
    def _fallback_forecast(self, forecast_days: int) -> Dict[str, Any]:
        """Fallback forecast for insufficient data"""
        daily_cost = 10.0  # $10/day baseline
        total_cost = daily_cost * forecast_days
        
        return {
            'usage': {
                'daily_compute_cost': Decimal('6.00'),
                'daily_storage_cost': Decimal('3.00'),
                'daily_network_cost': Decimal('1.00')
            },
            'cost': Decimal(str(total_cost)),
            'confidence': 0.3,
            'factors': ['insufficient_data', 'baseline_estimate'],
            'recommendations': [{
                'type': 'baseline',
                'message': 'Monitor actual usage and adjust budget as more data becomes available',
                'priority': 'medium'
            }]
        }
    
    def _generate_forecast_recommendations(self, predicted_cost: float, 
                                         avg_daily_cost: float, trend: float) -> List[Dict[str, Any]]:
        """Generate recommendations based on forecast"""
        recommendations = []
        
        if trend > avg_daily_cost * 0.1:  # Growing more than 10% of daily cost
            recommendations.append({
                'type': 'cost_optimization',
                'message': 'Usage is trending upward. Consider implementing auto-scaling limits.',
                'priority': 'high',
                'potential_savings': f'${trend * 30:.2f}/month'
            })
        
        if predicted_cost > avg_daily_cost * 40:  # More than 40 days of current usage
            recommendations.append({
                'type': 'budget_alert',
                'message': 'Forecasted costs are significantly higher than current usage',
                'priority': 'medium',
                'action': 'review_scaling_policies'
            })
        
        if avg_daily_cost < 5:  # Low usage
            recommendations.append({
                'type': 'optimization',
                'message': 'Consider reserved instances for consistent low usage',
                'priority': 'low',
                'potential_savings': '20-30%'
            })
        
        return recommendations
    
    def _generate_seasonal_recommendations(self, weekly_averages: Dict[int, float]) -> List[Dict[str, Any]]:
        """Generate recommendations based on seasonal patterns"""
        recommendations = []
        
        max_day = max(weekly_averages.items(), key=lambda x: x[1])
        min_day = min(weekly_averages.items(), key=lambda x: x[1])
        
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        if max_day[1] > min_day[1] * 1.5:  # 50% variance
            recommendations.append({
                'type': 'seasonal_scaling',
                'message': f'Peak usage on {day_names[max_day[0]]}, lowest on {day_names[min_day[0]]}',
                'priority': 'medium',
                'action': 'schedule_scaling_policies'
            })
        
        return recommendations
    
    def _generate_ml_recommendations(self, linear: Dict, exponential: Dict, seasonal: Dict) -> List[Dict[str, Any]]:
        """Generate ML-based recommendations"""
        recommendations = []
        
        # Compare model predictions
        costs = [linear['cost'], exponential['cost'], seasonal['cost']]
        max_cost = max(costs)
        min_cost = min(costs)
        
        if max_cost > min_cost * Decimal('1.3'):  # 30% variance between models
            recommendations.append({
                'type': 'uncertainty',
                'message': 'High variance between forecasting models - monitor closely',
                'priority': 'medium',
                'variance': f'{((max_cost - min_cost) / min_cost * 100):.1f}%'
            })
        
        return recommendations
    
    async def _store_forecast(self, forecast: UsageForecast):
        """Store forecast in database"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            await conn.execute("""
                INSERT INTO usage_forecasts 
                (forecast_id, user_id, org_id, forecast_period_days, model_used,
                 predicted_usage, predicted_cost, confidence_level, 
                 factors_considered, recommendations, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                forecast.forecast_id, forecast.user_id, forecast.org_id,
                forecast.forecast_period_days, forecast.model_used.value,
                json.dumps({k: str(v) for k, v in forecast.predicted_usage.items()}),
                float(forecast.predicted_cost), forecast.confidence_level,
                json.dumps(forecast.factors_considered),
                json.dumps(forecast.recommendations),
                forecast.created_at.isoformat()
            ))
            await conn.commit()
    
    # Budget Planning
    async def create_budget_plan(self, user_id: str, name: str, total_budget: Decimal,
                               period_months: int = 12, org_id: Optional[str] = None,
                               service_allocations: Optional[Dict[str, Decimal]] = None) -> BudgetPlan:
        """Create a new budget plan"""
        budget_id = f"budget_{uuid.uuid4().hex[:12]}"
        
        period_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(days=period_months * 30)
        monthly_budget = total_budget / period_months
        
        # Default service allocations if not provided
        if not service_allocations:
            service_allocations = {
                'compute': total_budget * Decimal('0.60'),
                'storage': total_budget * Decimal('0.25'),
                'network': total_budget * Decimal('0.10'),
                'other': total_budget * Decimal('0.05')
            }
        
        # Default alert thresholds
        alert_thresholds = {
            'warning': 75.0,    # 75% of budget
            'critical': 90.0,   # 90% of budget
            'emergency': 100.0  # 100% of budget
        }
        
        budget_plan = BudgetPlan(
            budget_id=budget_id,
            user_id=user_id,
            org_id=org_id,
            name=name,
            total_budget=total_budget,
            monthly_budget=monthly_budget,
            period_start=period_start,
            period_end=period_end,
            service_allocations=service_allocations,
            alert_thresholds=alert_thresholds
        )
        
        # Store budget plan
        await self._store_budget_plan(budget_plan)
        
        logger.info(f"Created budget plan {budget_id} for user {user_id}: ${total_budget} over {period_months} months")
        
        return budget_plan
    
    async def _store_budget_plan(self, budget: BudgetPlan):
        """Store budget plan in database"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            await conn.execute("""
                INSERT INTO budget_plans 
                (budget_id, user_id, org_id, name, total_budget, monthly_budget,
                 period_start, period_end, service_allocations, alert_thresholds,
                 current_spend, projected_spend, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                budget.budget_id, budget.user_id, budget.org_id, budget.name,
                float(budget.total_budget), float(budget.monthly_budget),
                budget.period_start.isoformat(), budget.period_end.isoformat(),
                json.dumps({k: str(v) for k, v in budget.service_allocations.items()}),
                json.dumps(budget.alert_thresholds),
                float(budget.current_spend), float(budget.projected_spend),
                budget.status, budget.created_at.isoformat()
            ))
            await conn.commit()
    
    async def update_budget_spend(self, budget_id: str) -> bool:
        """Update current spend for a budget"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            # Get budget details
            async with conn.execute("""
                SELECT user_id, period_start, period_end, total_budget, alert_thresholds
                FROM budget_plans WHERE budget_id = ?
            """, (budget_id,)) as cursor:
                budget_row = await cursor.fetchone()
                if not budget_row:
                    return False
                
                user_id, period_start, period_end, total_budget, alert_thresholds = budget_row
            
            # Calculate current spend
            period_start_dt = datetime.fromisoformat(period_start)
            period_end_dt = datetime.fromisoformat(period_end)
            now = datetime.now(timezone.utc)
            
            # Get actual spend to date
            async with conn.execute("""
                SELECT COALESCE(SUM(total_cost), 0) as current_spend
                FROM usage_records 
                WHERE user_id = ? AND created_at BETWEEN ? AND ?
            """, (user_id, period_start, now.isoformat())) as cursor:
                spend_row = await cursor.fetchone()
                current_spend = spend_row[0] if spend_row else 0
            
            # Generate forecast for remaining period
            remaining_days = (period_end_dt - now).days
            if remaining_days > 0:
                forecast = await self.generate_usage_forecast(user_id, remaining_days)
                projected_total = Decimal(str(current_spend)) + forecast.predicted_cost
            else:
                projected_total = Decimal(str(current_spend))
            
            # Update budget
            await conn.execute("""
                UPDATE budget_plans 
                SET current_spend = ?, projected_spend = ?
                WHERE budget_id = ?
            """, (current_spend, float(projected_total), budget_id))
            await conn.commit()
            
            # Check for budget alerts
            await self._check_budget_alerts(
                budget_id, user_id, Decimal(str(current_spend)), 
                Decimal(str(total_budget)), json.loads(alert_thresholds)
            )
            
        return True
    
    async def _check_budget_alerts(self, budget_id: str, user_id: str, 
                                 current_spend: Decimal, total_budget: Decimal,
                                 alert_thresholds: Dict[str, float]):
        """Check and trigger budget alerts if necessary"""
        percentage_used = float((current_spend / total_budget) * 100)
        
        # Determine alert level
        alert_level = None
        if percentage_used >= alert_thresholds.get('emergency', 100):
            alert_level = BudgetAlertLevel.EMERGENCY
        elif percentage_used >= alert_thresholds.get('critical', 90):
            alert_level = BudgetAlertLevel.CRITICAL
        elif percentage_used >= alert_thresholds.get('warning', 75):
            alert_level = BudgetAlertLevel.WARNING
        
        if alert_level:
            await self._create_budget_alert(
                budget_id, user_id, alert_level, percentage_used,
                current_spend - total_budget if current_spend > total_budget else Decimal('0')
            )
    
    async def _create_budget_alert(self, budget_id: str, user_id: str, 
                                 level: BudgetAlertLevel, percentage_used: float,
                                 amount_over: Decimal):
        """Create a budget alert"""
        alert_id = f"alert_{uuid.uuid4().hex[:12]}"
        
        messages = {
            BudgetAlertLevel.WARNING: f"Budget is {percentage_used:.1f}% used",
            BudgetAlertLevel.CRITICAL: f"Budget critically low: {percentage_used:.1f}% used",
            BudgetAlertLevel.EMERGENCY: f"Budget exceeded by ${amount_over:.2f}"
        }
        
        alert = BudgetAlert(
            alert_id=alert_id,
            budget_id=budget_id,
            user_id=user_id,
            level=level,
            message=messages.get(level, "Budget alert"),
            percentage_used=percentage_used,
            amount_over_budget=amount_over
        )
        
        # Store alert
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            await conn.execute("""
                INSERT INTO budget_alerts 
                (alert_id, budget_id, user_id, level, message, percentage_used,
                 amount_over_budget, triggered_at, acknowledged)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert_id, budget_id, user_id, level.value, alert.message,
                percentage_used, float(amount_over), alert.triggered_at.isoformat(), False
            ))
            await conn.commit()
        
        logger.warning(f"Budget alert {alert_id}: {alert.message}")
    
    async def get_user_budget_plans(self, user_id: str) -> List[Dict[str, Any]]:
        """Get budget plans for a user"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            async with conn.execute("""
                SELECT budget_id, name, total_budget, monthly_budget, 
                       period_start, period_end, current_spend, projected_spend,
                       status, created_at
                FROM budget_plans 
                WHERE user_id = ? AND status = 'active'
                ORDER BY created_at DESC
            """, (user_id,)) as cursor:
                budgets = []
                async for row in cursor:
                    budgets.append({
                        'budget_id': row[0],
                        'name': row[1],
                        'total_budget': float(row[2]),
                        'monthly_budget': float(row[3]),
                        'period_start': row[4],
                        'period_end': row[5],
                        'current_spend': float(row[6]),
                        'projected_spend': float(row[7]),
                        'status': row[8],
                        'created_at': row[9],
                        'percentage_used': (float(row[6]) / float(row[2])) * 100 if row[2] > 0 else 0
                    })
                return budgets
    
    async def get_budget_alerts(self, user_id: str, acknowledged: bool = False) -> List[Dict[str, Any]]:
        """Get budget alerts for a user"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            async with conn.execute("""
                SELECT a.alert_id, a.budget_id, a.level, a.message, a.percentage_used,
                       a.amount_over_budget, a.triggered_at, a.acknowledged,
                       b.name as budget_name
                FROM budget_alerts a
                JOIN budget_plans b ON a.budget_id = b.budget_id
                WHERE a.user_id = ? AND a.acknowledged = ?
                ORDER BY a.triggered_at DESC
            """, (user_id, acknowledged)) as cursor:
                alerts = []
                async for row in cursor:
                    alerts.append({
                        'alert_id': row[0],
                        'budget_id': row[1],
                        'level': row[2],
                        'message': row[3],
                        'percentage_used': row[4],
                        'amount_over_budget': float(row[5]),
                        'triggered_at': row[6],
                        'acknowledged': bool(row[7]),
                        'budget_name': row[8]
                    })
                return alerts
    
    # Dashboard and Analytics
    async def get_forecasting_dashboard(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive forecasting and budget dashboard"""
        # Get recent forecasts
        forecasts = await self._get_recent_forecasts(user_id, limit=3)
        
        # Get active budgets
        budgets = await self.get_user_budget_plans(user_id)
        
        # Get unacknowledged alerts
        alerts = await self.get_budget_alerts(user_id, acknowledged=False)
        
        # Calculate summary metrics
        total_budgeted = sum(b['total_budget'] for b in budgets)
        total_current_spend = sum(b['current_spend'] for b in budgets)
        total_projected_spend = sum(b['projected_spend'] for b in budgets)
        
        # Budget utilization
        avg_utilization = (total_current_spend / total_budgeted * 100) if total_budgeted > 0 else 0
        
        return {
            'forecasting': {
                'recent_forecasts': len(forecasts),
                'average_confidence': sum(f.get('confidence_level', 0) for f in forecasts) / len(forecasts) if forecasts else 0,
                'next_30_day_prediction': forecasts[0].get('predicted_cost', 0) if forecasts else 0
            },
            'budgets': {
                'active_budgets': len(budgets),
                'total_budget': total_budgeted,
                'current_spend': total_current_spend,
                'projected_spend': total_projected_spend,
                'average_utilization': avg_utilization,
                'on_track': total_projected_spend <= total_budgeted
            },
            'alerts': {
                'total_alerts': len(alerts),
                'critical_alerts': len([a for a in alerts if a['level'] in ['critical', 'emergency']]),
                'warning_alerts': len([a for a in alerts if a['level'] == 'warning']),
                'recent_alerts': alerts[:5]
            },
            'recommendations': await self._get_dashboard_recommendations(user_id, budgets, alerts)
        }
    
    async def _get_recent_forecasts(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent forecasts for a user"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            async with conn.execute("""
                SELECT forecast_id, forecast_period_days, model_used, predicted_cost,
                       confidence_level, created_at
                FROM usage_forecasts 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit)) as cursor:
                forecasts = []
                async for row in cursor:
                    forecasts.append({
                        'forecast_id': row[0],
                        'forecast_period_days': row[1],
                        'model_used': row[2],
                        'predicted_cost': float(row[3]),
                        'confidence_level': row[4],
                        'created_at': row[5]
                    })
                return forecasts
    
    async def _get_dashboard_recommendations(self, user_id: str, budgets: List[Dict], alerts: List[Dict]) -> List[Dict[str, Any]]:
        """Generate dashboard recommendations"""
        recommendations = []
        
        # Budget recommendations
        if not budgets:
            recommendations.append({
                'type': 'budget_setup',
                'priority': 'high',
                'message': 'Set up your first budget to track spending and avoid surprises',
                'action': 'create_budget'
            })
        
        # Alert recommendations
        critical_alerts = [a for a in alerts if a['level'] in ['critical', 'emergency']]
        if critical_alerts:
            recommendations.append({
                'type': 'urgent_action',
                'priority': 'critical',
                'message': f'{len(critical_alerts)} critical budget alerts need immediate attention',
                'action': 'review_alerts'
            })
        
        # Forecast recommendations
        forecasts = await self._get_recent_forecasts(user_id, limit=1)
        if forecasts and forecasts[0]['confidence_level'] < 0.5:
            recommendations.append({
                'type': 'data_quality',
                'priority': 'medium',
                'message': 'Low forecast confidence - more usage history needed for accurate predictions',
                'action': 'monitor_usage'
            })
        
        return recommendations