"""
Cost Optimization System

Track resource usage costs, warn before expensive operations, optimize
API usage, batch operations, and provide cost-aware scheduling.
"""

import asyncio
import time
import logging
import json
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
import calendar

from config.settings import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CostCategory(Enum):
    """Categories of costs"""
    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORK = "network"
    API_CALLS = "api_calls"
    DATA_PROCESSING = "data_processing"
    AI_ML = "ai_ml"
    DATABASE = "database"
    THIRD_PARTY = "third_party"

class BillingModel(Enum):
    """Billing models"""
    PAY_PER_USE = "pay_per_use"
    SUBSCRIPTION = "subscription"
    TIERED = "tiered"
    FREE_TIER = "free_tier"
    PREPAID = "prepaid"

class CostAlert(Enum):
    """Cost alert levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    BUDGET_EXCEEDED = "budget_exceeded"

@dataclass
class CostMetric:
    """Individual cost metric"""
    metric_id: str
    timestamp: datetime
    category: CostCategory
    service_name: str
    resource_type: str
    quantity: float
    unit: str
    unit_cost: float
    total_cost: float
    billing_model: BillingModel
    metadata: Dict[str, Any]
    
    def to_dict(self):
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['category'] = self.category.value
        data['billing_model'] = self.billing_model.value
        return data

@dataclass
class CostBudget:
    """Cost budget definition"""
    budget_id: str
    name: str
    category: Optional[CostCategory]
    service_name: Optional[str]
    period: str  # 'daily', 'weekly', 'monthly', 'yearly'
    amount: float
    currency: str
    alert_thresholds: Dict[CostAlert, float]  # percentage thresholds
    start_date: datetime
    end_date: Optional[datetime]
    active: bool = True
    
    def to_dict(self):
        data = asdict(self)
        data['category'] = self.category.value if self.category else None
        data['alert_thresholds'] = {k.value: v for k, v in self.alert_thresholds.items()}
        data['start_date'] = self.start_date.isoformat()
        if self.end_date:
            data['end_date'] = self.end_date.isoformat()
        return data

@dataclass
class CostAlert:
    """Cost alert notification"""
    alert_id: str
    timestamp: datetime
    alert_level: CostAlert
    budget_id: str
    current_spending: float
    budget_amount: float
    percentage_used: float
    message: str
    acknowledged: bool = False
    
    def to_dict(self):
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['alert_level'] = self.alert_level.value
        return data

@dataclass
class CostOptimizationSuggestion:
    """Cost optimization suggestion"""
    suggestion_id: str
    timestamp: datetime
    category: CostCategory
    service_name: str
    current_cost: float
    potential_savings: float
    confidence: float  # 0.0 - 1.0
    title: str
    description: str
    implementation_effort: str  # 'low', 'medium', 'high'
    impact: str  # 'low', 'medium', 'high'
    actions: List[str]
    
    def to_dict(self):
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['category'] = self.category.value
        return data

class ServiceCostCalculator:
    """Calculate costs for different services"""
    
    def __init__(self):
        # Cost rates (USD)
        self.rates = {
            'compute_per_hour': 0.10,
            'memory_per_gb_hour': 0.01,
            'storage_per_gb_month': 0.023,
            'network_per_gb': 0.12,
            'api_call_base': 0.001,
            'database_per_gb_month': 0.25,
            'ai_processing_per_token': 0.00002,
            'data_processing_per_gb': 0.05
        }
        
        # Free tier limits
        self.free_tiers = {
            'compute_hours_monthly': 750,
            'storage_gb_monthly': 15,
            'network_gb_monthly': 15,
            'api_calls_monthly': 1000000,
            'database_gb_monthly': 0.5
        }
        
        # Service-specific multipliers
        self.service_multipliers = {
            'premium_compute': 2.0,
            'gpu_compute': 5.0,
            'enterprise_storage': 1.5,
            'realtime_api': 3.0,
            'ml_inference': 2.5
        }
    
    def calculate_compute_cost(self, cpu_hours: float, memory_gb_hours: float, 
                             service_tier: str = 'standard') -> float:
        """Calculate compute costs"""
        multiplier = self.service_multipliers.get(service_tier, 1.0)
        
        cpu_cost = cpu_hours * self.rates['compute_per_hour'] * multiplier
        memory_cost = memory_gb_hours * self.rates['memory_per_gb_hour'] * multiplier
        
        return cpu_cost + memory_cost
    
    def calculate_storage_cost(self, storage_gb: float, days: float, 
                             service_tier: str = 'standard') -> float:
        """Calculate storage costs"""
        multiplier = self.service_multipliers.get(service_tier, 1.0)
        monthly_rate = self.rates['storage_per_gb_month'] * multiplier
        
        return storage_gb * (days / 30.44) * monthly_rate  # 30.44 avg days/month
    
    def calculate_network_cost(self, data_gb: float, operation_type: str = 'outbound') -> float:
        """Calculate network transfer costs"""
        if operation_type == 'inbound':
            return 0.0  # Inbound is typically free
        
        # Apply free tier
        free_allowance = self.free_tiers['network_gb_monthly']
        billable_gb = max(0, data_gb - free_allowance)
        
        return billable_gb * self.rates['network_per_gb']
    
    def calculate_api_cost(self, api_calls: int, complexity_factor: float = 1.0) -> float:
        """Calculate API call costs"""
        # Apply free tier
        free_allowance = self.free_tiers['api_calls_monthly']
        billable_calls = max(0, api_calls - free_allowance)
        
        return billable_calls * self.rates['api_call_base'] * complexity_factor
    
    def calculate_database_cost(self, storage_gb: float, read_operations: int, 
                              write_operations: int, days: float = 30) -> float:
        """Calculate database costs"""
        # Storage cost
        storage_cost = self.calculate_storage_cost(storage_gb, days, 'database')
        
        # Operation costs (simplified)
        operation_cost = (read_operations * 0.0001) + (write_operations * 0.0002)
        
        return storage_cost + operation_cost
    
    def calculate_ai_processing_cost(self, tokens_processed: int, model_complexity: str = 'standard') -> float:
        """Calculate AI/ML processing costs"""
        complexity_multipliers = {
            'simple': 0.5,
            'standard': 1.0,
            'advanced': 2.0,
            'premium': 5.0
        }
        
        multiplier = complexity_multipliers.get(model_complexity, 1.0)
        return tokens_processed * self.rates['ai_processing_per_token'] * multiplier

class FreeTierManager:
    """Manage free tier usage and tracking"""
    
    def __init__(self):
        self.usage_tracking = defaultdict(float)
        self.monthly_limits = config.cost_settings.copy()
        self.reset_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    def check_monthly_reset(self):
        """Check if monthly usage should be reset"""
        now = datetime.now()
        if now.month != self.reset_date.month or now.year != self.reset_date.year:
            self.usage_tracking.clear()
            self.reset_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            logger.info("Monthly free tier usage reset")
    
    def can_use_free_tier(self, service: str, amount: float) -> Tuple[bool, float]:
        """Check if free tier can be used for this amount"""
        self.check_monthly_reset()
        
        service_key = f"free_tier_{service}"
        if service_key not in self.monthly_limits:
            return False, amount
        
        current_usage = self.usage_tracking[service]
        limit = self.monthly_limits[service_key]
        
        if current_usage >= limit:
            return False, amount
        
        free_amount = min(amount, limit - current_usage)
        billable_amount = amount - free_amount
        
        return free_amount > 0, billable_amount
    
    def record_usage(self, service: str, amount: float):
        """Record usage against free tier"""
        self.usage_tracking[service] += amount
    
    def get_free_tier_status(self) -> Dict[str, Any]:
        """Get current free tier usage status"""
        self.check_monthly_reset()
        
        status = {}
        for service, limit in self.monthly_limits.items():
            if service.startswith('free_tier_'):
                service_name = service.replace('free_tier_', '')
                current = self.usage_tracking[service_name]
                
                status[service_name] = {
                    'limit': limit,
                    'used': current,
                    'remaining': max(0, limit - current),
                    'percentage_used': (current / limit * 100) if limit > 0 else 0
                }
        
        return status

class CostOptimizer:
    """Main cost optimization engine"""
    
    def __init__(self):
        self.cost_metrics = deque(maxlen=10000)
        self.budgets = {}
        self.alerts = deque(maxlen=1000)
        self.suggestions = []
        
        self.calculator = ServiceCostCalculator()
        self.free_tier_manager = FreeTierManager()
        
        # Cost tracking by period
        self.daily_costs = defaultdict(float)
        self.monthly_costs = defaultdict(float)
        self.yearly_costs = defaultdict(float)
        
        # Optimization settings
        self.batch_operations = True
        self.off_peak_scheduling = True
        self.cost_aware_scaling = True
        self.auto_optimization = True
        
        # Callbacks
        self.cost_callbacks = []
        
    def add_cost_callback(self, callback: Callable):
        """Add cost alert callback"""
        self.cost_callbacks.append(callback)
    
    def record_cost(self, category: CostCategory, service_name: str, resource_type: str,
                   quantity: float, unit: str, unit_cost: float = None, 
                   billing_model: BillingModel = BillingModel.PAY_PER_USE,
                   metadata: Dict[str, Any] = None) -> str:
        """Record a cost metric"""
        # Calculate cost based on category
        if unit_cost is None:
            unit_cost = self._get_default_unit_cost(category, resource_type)
        
        # Check free tier usage
        can_use_free, billable_quantity = self.free_tier_manager.can_use_free_tier(
            resource_type, quantity)
        
        if can_use_free:
            self.free_tier_manager.record_usage(resource_type, quantity - billable_quantity)
        
        total_cost = billable_quantity * unit_cost
        
        metric = CostMetric(
            metric_id=f"cost_{int(time.time() * 1000)}",
            timestamp=datetime.now(),
            category=category,
            service_name=service_name,
            resource_type=resource_type,
            quantity=quantity,
            unit=unit,
            unit_cost=unit_cost,
            total_cost=total_cost,
            billing_model=billing_model,
            metadata=metadata or {}
        )
        
        self.cost_metrics.append(metric)
        self._update_cost_aggregates(metric)
        
        # Check budgets
        asyncio.create_task(self._check_budgets(metric))
        
        logger.debug(f"Recorded cost: {service_name} {resource_type} = ${total_cost:.4f}")
        
        return metric.metric_id
    
    def _get_default_unit_cost(self, category: CostCategory, resource_type: str) -> float:
        """Get default unit cost for resource type"""
        cost_mapping = {
            (CostCategory.COMPUTE, 'cpu_hour'): self.calculator.rates['compute_per_hour'],
            (CostCategory.COMPUTE, 'memory_gb_hour'): self.calculator.rates['memory_per_gb_hour'],
            (CostCategory.STORAGE, 'gb_month'): self.calculator.rates['storage_per_gb_month'],
            (CostCategory.NETWORK, 'gb'): self.calculator.rates['network_per_gb'],
            (CostCategory.API_CALLS, 'call'): self.calculator.rates['api_call_base'],
            (CostCategory.DATABASE, 'gb_month'): self.calculator.rates['database_per_gb_month'],
            (CostCategory.AI_ML, 'token'): self.calculator.rates['ai_processing_per_token'],
            (CostCategory.DATA_PROCESSING, 'gb'): self.calculator.rates['data_processing_per_gb']
        }
        
        return cost_mapping.get((category, resource_type), 0.01)
    
    def _update_cost_aggregates(self, metric: CostMetric):
        """Update cost aggregates"""
        date_key = metric.timestamp.strftime('%Y-%m-%d')
        month_key = metric.timestamp.strftime('%Y-%m')
        year_key = metric.timestamp.strftime('%Y')
        
        self.daily_costs[date_key] += metric.total_cost
        self.monthly_costs[month_key] += metric.total_cost
        self.yearly_costs[year_key] += metric.total_cost
    
    async def _check_budgets(self, metric: CostMetric):
        """Check if any budgets are exceeded"""
        for budget_id, budget in self.budgets.items():
            if not budget.active:
                continue
            
            # Check if metric applies to this budget
            if budget.category and budget.category != metric.category:
                continue
            
            if budget.service_name and budget.service_name != metric.service_name:
                continue
            
            # Calculate current spending for budget period
            current_spending = self._calculate_budget_spending(budget)
            percentage_used = (current_spending / budget.amount) * 100
            
            # Check alert thresholds
            for alert_level, threshold in budget.alert_thresholds.items():
                if percentage_used >= threshold:
                    await self._create_budget_alert(budget, alert_level, current_spending, percentage_used)
    
    def _calculate_budget_spending(self, budget: CostBudget) -> float:
        """Calculate current spending for a budget period"""
        now = datetime.now()
        
        if budget.period == 'daily':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif budget.period == 'weekly':
            days_since_monday = now.weekday()
            start_date = now - timedelta(days=days_since_monday)
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif budget.period == 'monthly':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:  # yearly
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Sum costs in the period
        total = 0.0
        for metric in self.cost_metrics:
            if metric.timestamp >= start_date:
                # Apply filters
                if budget.category and budget.category != metric.category:
                    continue
                if budget.service_name and budget.service_name != metric.service_name:
                    continue
                
                total += metric.total_cost
        
        return total
    
    async def _create_budget_alert(self, budget: CostBudget, alert_level: CostAlert, 
                                 current_spending: float, percentage_used: float):
        """Create budget alert"""
        # Check if we already have a recent alert for this level
        recent_alerts = [a for a in self.alerts 
                        if a.budget_id == budget.budget_id 
                        and a.alert_level == alert_level
                        and (datetime.now() - a.timestamp).seconds < 3600]  # 1 hour
        
        if recent_alerts:
            return  # Don't spam alerts
        
        alert = CostAlert(
            alert_id=f"alert_{int(time.time() * 1000)}",
            timestamp=datetime.now(),
            alert_level=alert_level,
            budget_id=budget.budget_id,
            current_spending=current_spending,
            budget_amount=budget.amount,
            percentage_used=percentage_used,
            message=f"Budget '{budget.name}' is at {percentage_used:.1f}% (${current_spending:.2f} / ${budget.amount:.2f})"
        )
        
        self.alerts.append(alert)
        
        # Notify callbacks
        for callback in self.cost_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error(f"Cost callback error: {e}")
        
        logger.warning(f"Cost alert: {alert.message}")
    
    def create_budget(self, name: str, amount: float, period: str = 'monthly',
                     category: CostCategory = None, service_name: str = None,
                     alert_thresholds: Dict[str, float] = None) -> str:
        """Create a cost budget"""
        budget_id = f"budget_{int(time.time() * 1000)}"
        
        # Default alert thresholds
        if alert_thresholds is None:
            alert_thresholds = {
                CostAlert.WARNING: 75.0,
                CostAlert.CRITICAL: 90.0,
                CostAlert.BUDGET_EXCEEDED: 100.0
            }
        else:
            # Convert string keys to enum
            threshold_enums = {}
            for key, value in alert_thresholds.items():
                if isinstance(key, str):
                    threshold_enums[CostAlert(key)] = value
                else:
                    threshold_enums[key] = value
            alert_thresholds = threshold_enums
        
        budget = CostBudget(
            budget_id=budget_id,
            name=name,
            category=category,
            service_name=service_name,
            period=period,
            amount=amount,
            currency='USD',
            alert_thresholds=alert_thresholds,
            start_date=datetime.now(),
            end_date=None
        )
        
        self.budgets[budget_id] = budget
        logger.info(f"Created budget '{name}': ${amount} {period}")
        
        return budget_id
    
    async def estimate_operation_cost(self, operation: str, parameters: Dict[str, Any]) -> float:
        """Estimate cost of an operation before executing"""
        if operation == 'compute_task':
            cpu_hours = parameters.get('cpu_hours', 0.1)
            memory_gb_hours = parameters.get('memory_gb_hours', 0.1)
            return self.calculator.calculate_compute_cost(cpu_hours, memory_gb_hours)
        
        elif operation == 'data_transfer':
            data_gb = parameters.get('data_gb', 0.001)
            return self.calculator.calculate_network_cost(data_gb)
        
        elif operation == 'api_calls':
            call_count = parameters.get('call_count', 1)
            complexity = parameters.get('complexity_factor', 1.0)
            return self.calculator.calculate_api_cost(call_count, complexity)
        
        elif operation == 'storage':
            storage_gb = parameters.get('storage_gb', 0.1)
            days = parameters.get('days', 1)
            return self.calculator.calculate_storage_cost(storage_gb, days)
        
        elif operation == 'ai_processing':
            tokens = parameters.get('tokens', 1000)
            complexity = parameters.get('model_complexity', 'standard')
            return self.calculator.calculate_ai_processing_cost(tokens, complexity)
        
        else:
            # Default estimation
            return parameters.get('estimated_cost', 0.01)
    
    async def should_proceed_with_operation(self, operation: str, parameters: Dict[str, Any],
                                          cost_threshold: float = None) -> Tuple[bool, float, str]:
        """Check if operation should proceed based on cost"""
        estimated_cost = await self.estimate_operation_cost(operation, parameters)
        
        # Use default threshold from config if not provided
        if cost_threshold is None:
            cost_threshold = config.cost_settings['warn_expensive_threshold']
        
        # Check if cost exceeds threshold
        if estimated_cost > cost_threshold:
            return False, estimated_cost, f"Operation cost (${estimated_cost:.4f}) exceeds threshold (${cost_threshold:.2f})"
        
        # Check budget implications
        today = datetime.now().strftime('%Y-%m-%d')
        current_daily_cost = self.daily_costs[today]
        
        for budget in self.budgets.values():
            if budget.period == 'daily' and budget.active:
                projected_cost = current_daily_cost + estimated_cost
                if projected_cost > budget.amount:
                    return False, estimated_cost, f"Operation would exceed daily budget '{budget.name}'"
        
        return True, estimated_cost, "OK"
    
    def get_cost_breakdown(self, period: str = 'monthly', 
                          start_date: datetime = None) -> Dict[str, Any]:
        """Get cost breakdown by category and service"""
        if start_date is None:
            now = datetime.now()
            if period == 'daily':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == 'weekly':
                start_date = now - timedelta(days=now.weekday())
                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == 'monthly':
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            else:  # yearly
                start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Filter metrics by period
        period_metrics = [m for m in self.cost_metrics if m.timestamp >= start_date]
        
        # Aggregate by category
        by_category = defaultdict(float)
        by_service = defaultdict(float)
        by_resource_type = defaultdict(float)
        
        total_cost = 0.0
        
        for metric in period_metrics:
            by_category[metric.category.value] += metric.total_cost
            by_service[metric.service_name] += metric.total_cost
            by_resource_type[metric.resource_type] += metric.total_cost
            total_cost += metric.total_cost
        
        return {
            'period': period,
            'start_date': start_date.isoformat(),
            'total_cost': total_cost,
            'by_category': dict(by_category),
            'by_service': dict(by_service),
            'by_resource_type': dict(by_resource_type),
            'metric_count': len(period_metrics)
        }
    
    def generate_optimization_suggestions(self) -> List[CostOptimizationSuggestion]:
        """Generate cost optimization suggestions"""
        suggestions = []
        
        # Analyze recent costs
        recent_costs = list(self.cost_metrics)[-1000:]  # Last 1000 metrics
        
        if not recent_costs:
            return suggestions
        
        # Group by service
        service_costs = defaultdict(float)
        service_metrics = defaultdict(list)
        
        for metric in recent_costs:
            service_costs[metric.service_name] += metric.total_cost
            service_metrics[metric.service_name].append(metric)
        
        # Find expensive services
        sorted_services = sorted(service_costs.items(), key=lambda x: x[1], reverse=True)
        
        for service_name, total_cost in sorted_services[:5]:  # Top 5 expensive services
            metrics = service_metrics[service_name]
            
            # Analyze patterns
            avg_cost_per_metric = total_cost / len(metrics)
            
            if avg_cost_per_metric > 0.10:  # High cost per operation
                suggestions.append(CostOptimizationSuggestion(
                    suggestion_id=f"opt_{int(time.time() * 1000)}",
                    timestamp=datetime.now(),
                    category=metrics[0].category,
                    service_name=service_name,
                    current_cost=total_cost,
                    potential_savings=total_cost * 0.3,  # Estimate 30% savings
                    confidence=0.7,
                    title=f"Optimize {service_name} usage",
                    description=f"Service '{service_name}' has high per-operation costs (${avg_cost_per_metric:.4f})",
                    implementation_effort="medium",
                    impact="high",
                    actions=[
                        "Batch operations to reduce overhead",
                        "Use cheaper service tiers when possible",
                        "Implement caching to reduce redundant operations",
                        "Schedule non-urgent operations for off-peak hours"
                    ]
                ))
            
            # Check for frequently used expensive resources
            resource_usage = defaultdict(int)
            resource_costs = defaultdict(float)
            
            for metric in metrics:
                resource_usage[metric.resource_type] += 1
                resource_costs[metric.resource_type] += metric.total_cost
            
            for resource_type, usage_count in resource_usage.items():
                if usage_count > 50 and resource_costs[resource_type] > 1.0:  # Frequent and expensive
                    suggestions.append(CostOptimizationSuggestion(
                        suggestion_id=f"opt_{int(time.time() * 1000)}",
                        timestamp=datetime.now(),
                        category=metrics[0].category,
                        service_name=service_name,
                        current_cost=resource_costs[resource_type],
                        potential_savings=resource_costs[resource_type] * 0.25,
                        confidence=0.8,
                        title=f"Optimize {resource_type} usage in {service_name}",
                        description=f"Resource '{resource_type}' is used frequently ({usage_count} times) with high costs",
                        implementation_effort="low",
                        impact="medium",
                        actions=[
                            f"Cache {resource_type} results when possible",
                            "Batch multiple operations together",
                            "Consider alternative cheaper resources",
                            "Implement usage quotas and limits"
                        ]
                    ))
        
        # Check for free tier optimization
        free_tier_status = self.free_tier_manager.get_free_tier_status()
        for service, status in free_tier_status.items():
            if status['percentage_used'] < 50:  # Under-utilizing free tier
                suggestions.append(CostOptimizationSuggestion(
                    suggestion_id=f"opt_{int(time.time() * 1000)}",
                    timestamp=datetime.now(),
                    category=CostCategory.THIRD_PARTY,
                    service_name=service,
                    current_cost=0.0,
                    potential_savings=0.0,
                    confidence=0.9,
                    title=f"Utilize more of {service} free tier",
                    description=f"Only using {status['percentage_used']:.1f}% of free {service} allowance",
                    implementation_effort="low",
                    impact="low",
                    actions=[
                        f"Increase usage of {service} to maximize free tier benefits",
                        "Move workloads from paid services to free tier when possible",
                        "Set up monitoring to track free tier usage"
                    ]
                ))
        
        self.suggestions = suggestions
        return suggestions
    
    def get_cost_forecast(self, days_ahead: int = 30) -> Dict[str, Any]:
        """Generate cost forecast"""
        # Simple linear projection based on recent trends
        recent_days = 14
        end_date = datetime.now()
        start_date = end_date - timedelta(days=recent_days)
        
        # Get daily costs for trend analysis
        daily_totals = defaultdict(float)
        for metric in self.cost_metrics:
            if metric.timestamp >= start_date:
                day_key = metric.timestamp.strftime('%Y-%m-%d')
                daily_totals[day_key] += metric.total_cost
        
        if not daily_totals:
            return {'forecast': 0.0, 'confidence': 0.0}
        
        # Calculate trend
        costs = list(daily_totals.values())
        if len(costs) > 1:
            daily_avg = np.mean(costs)
            trend = np.polyfit(range(len(costs)), costs, 1)[0]  # Linear trend
        else:
            daily_avg = costs[0] if costs else 0.0
            trend = 0.0
        
        # Project forward
        forecasted_daily_cost = daily_avg + (trend * days_ahead / 2)  # Average over period
        total_forecast = forecasted_daily_cost * days_ahead
        
        # Calculate confidence based on trend stability
        if len(costs) > 2:
            cost_variance = np.var(costs)
            confidence = max(0.1, min(0.9, 1.0 - (cost_variance / daily_avg) if daily_avg > 0 else 0.1))
        else:
            confidence = 0.5
        
        return {
            'forecast_period_days': days_ahead,
            'forecasted_total_cost': total_forecast,
            'forecasted_daily_average': forecasted_daily_cost,
            'confidence': confidence,
            'trend_direction': 'increasing' if trend > 0 else 'decreasing' if trend < 0 else 'stable',
            'daily_trend': trend,
            'current_daily_average': daily_avg
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive cost optimization status"""
        # Current period costs
        daily_breakdown = self.get_cost_breakdown('daily')
        monthly_breakdown = self.get_cost_breakdown('monthly')
        
        # Budget status
        budget_status = {}
        for budget_id, budget in self.budgets.items():
            current_spending = self._calculate_budget_spending(budget)
            percentage_used = (current_spending / budget.amount) * 100
            
            budget_status[budget_id] = {
                'name': budget.name,
                'period': budget.period,
                'budget_amount': budget.amount,
                'current_spending': current_spending,
                'percentage_used': percentage_used,
                'remaining': budget.amount - current_spending,
                'status': 'over_budget' if percentage_used > 100 else 
                         'critical' if percentage_used > 90 else
                         'warning' if percentage_used > 75 else 'ok'
            }
        
        # Free tier status
        free_tier_status = self.free_tier_manager.get_free_tier_status()
        
        # Recent alerts
        recent_alerts = [alert.to_dict() for alert in list(self.alerts)[-10:]]
        
        # Optimization suggestions
        suggestions = self.generate_optimization_suggestions()
        
        # Cost forecast
        forecast = self.get_cost_forecast(30)
        
        return {
            'cost_optimization': {
                'total_metrics_recorded': len(self.cost_metrics),
                'optimization_enabled': self.auto_optimization,
                'batch_operations_enabled': self.batch_operations,
                'off_peak_scheduling_enabled': self.off_peak_scheduling
            },
            'current_costs': {
                'daily': daily_breakdown,
                'monthly': monthly_breakdown
            },
            'budgets': budget_status,
            'free_tier': free_tier_status,
            'recent_alerts': recent_alerts,
            'optimization_suggestions': [s.to_dict() for s in suggestions[:5]],
            'forecast': forecast,
            'settings': {
                'auto_optimization': self.auto_optimization,
                'cost_threshold_warning': config.cost_settings['warn_expensive_threshold'],
                'batch_operations': self.batch_operations,
                'off_peak_scheduling': self.off_peak_scheduling
            }
        }

# Global cost optimizer instance
cost_optimizer = CostOptimizer()

# Utility functions
async def estimate_and_warn(operation: str, parameters: Dict[str, Any], 
                          threshold: float = None) -> Tuple[bool, float]:
    """Estimate cost and warn if expensive"""
    can_proceed, cost, message = await cost_optimizer.should_proceed_with_operation(
        operation, parameters, threshold)
    
    if not can_proceed:
        logger.warning(f"Expensive operation blocked: {message}")
    
    return can_proceed, cost

def record_compute_usage(service_name: str, cpu_hours: float, memory_gb_hours: float):
    """Record compute usage"""
    cost_optimizer.record_cost(
        CostCategory.COMPUTE, service_name, 'cpu_hour', cpu_hours)
    cost_optimizer.record_cost(
        CostCategory.COMPUTE, service_name, 'memory_gb_hour', memory_gb_hours)

def record_storage_usage(service_name: str, storage_gb: float):
    """Record storage usage"""
    cost_optimizer.record_cost(
        CostCategory.STORAGE, service_name, 'gb_month', storage_gb)

def record_api_usage(service_name: str, call_count: int, complexity_factor: float = 1.0):
    """Record API usage"""
    cost_optimizer.record_cost(
        CostCategory.API_CALLS, service_name, 'call', call_count, 
        unit_cost=cost_optimizer.calculator.rates['api_call_base'] * complexity_factor)

if __name__ == "__main__":
    # Demo usage
    async def cost_alert_callback(alert):
        print(f"COST ALERT: {alert.message}")
    
    async def main():
        # Add callback
        cost_optimizer.add_cost_callback(cost_alert_callback)
        
        # Create budgets
        daily_budget = cost_optimizer.create_budget("Daily Operations", 10.0, "daily")
        monthly_budget = cost_optimizer.create_budget("Monthly Services", 100.0, "monthly")
        
        print("Created budgets:")
        print(f"- Daily: ${10.0}")
        print(f"- Monthly: ${100.0}")
        
        # Record some usage
        record_compute_usage("web_service", 0.5, 1.0)  # 0.5 CPU hours, 1 GB-hour memory
        record_storage_usage("database", 2.5)  # 2.5 GB storage
        record_api_usage("external_api", 150, 2.0)  # 150 calls with 2x complexity
        
        # Test expensive operation
        can_proceed, cost = await estimate_and_warn(
            'compute_task', 
            {'cpu_hours': 10.0, 'memory_gb_hours': 20.0}  # Expensive operation
        )
        
        print(f"\nExpensive operation check:")
        print(f"Can proceed: {can_proceed}")
        print(f"Estimated cost: ${cost:.4f}")
        
        # Generate cost breakdown
        breakdown = cost_optimizer.get_cost_breakdown('daily')
        print(f"\nDaily cost breakdown:")
        print(f"Total: ${breakdown['total_cost']:.4f}")
        print(f"By category: {breakdown['by_category']}")
        
        # Get optimization suggestions
        suggestions = cost_optimizer.generate_optimization_suggestions()
        print(f"\nOptimization suggestions:")
        for suggestion in suggestions[:3]:
            print(f"- {suggestion.title}")
            print(f"  Potential savings: ${suggestion.potential_savings:.4f}")
            print(f"  Implementation: {suggestion.implementation_effort}")
        
        # Get cost forecast
        forecast = cost_optimizer.get_cost_forecast(7)
        print(f"\n7-day cost forecast:")
        print(f"Forecasted total: ${forecast['forecasted_total_cost']:.2f}")
        print(f"Daily average: ${forecast['forecasted_daily_average']:.2f}")
        print(f"Confidence: {forecast['confidence']:.1%}")
        
        # System status
        status = cost_optimizer.get_system_status()
        print(f"\nSystem status:")
        print(f"Total metrics: {status['cost_optimization']['total_metrics_recorded']}")
        print(f"Monthly spending: ${status['current_costs']['monthly']['total_cost']:.2f}")
    
    asyncio.run(main())