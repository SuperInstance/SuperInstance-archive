import asyncio
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from models.monetization_models import *

class UsageMeteringManager:
    def __init__(self):
        self.usage_records = {}
        self.pricing_tiers = {
            PricingTier.FREE: {
                UsageMetric.REQUESTS: Decimal("0.00"),
                UsageMetric.BANDWIDTH: Decimal("0.00"),
                UsageMetric.STORAGE: Decimal("0.00"),
                UsageMetric.COMPUTE_TIME: Decimal("0.00")
            },
            PricingTier.BASIC: {
                UsageMetric.REQUESTS: Decimal("0.01"),
                UsageMetric.BANDWIDTH: Decimal("0.05"),
                UsageMetric.STORAGE: Decimal("0.02"),
                UsageMetric.COMPUTE_TIME: Decimal("0.10")
            },
            PricingTier.PRO: {
                UsageMetric.REQUESTS: Decimal("0.005"),
                UsageMetric.BANDWIDTH: Decimal("0.03"),
                UsageMetric.STORAGE: Decimal("0.015"),
                UsageMetric.COMPUTE_TIME: Decimal("0.08")
            },
            PricingTier.ENTERPRISE: {
                UsageMetric.REQUESTS: Decimal("0.002"),
                UsageMetric.BANDWIDTH: Decimal("0.02"),
                UsageMetric.STORAGE: Decimal("0.01"),
                UsageMetric.COMPUTE_TIME: Decimal("0.05")
            }
        }
        self.daily_usage = {}
        self.monthly_usage = {}
        
    async def record_usage(self, request: UsageMeteringRequest) -> UsageMeteringResponse:
        usage_id = str(uuid.uuid4())
        timestamp = request.timestamp or datetime.now()
        
        api_key_tier = await self._get_api_key_tier(request.api_key)
        cost = self._calculate_cost(request.metric_type, request.value, api_key_tier)
        
        usage_record = {
            "usage_id": usage_id,
            "api_key": request.api_key,
            "endpoint": request.endpoint,
            "metric_type": request.metric_type,
            "value": request.value,
            "cost": cost,
            "tier": api_key_tier,
            "timestamp": timestamp,
            "metadata": request.metadata
        }
        
        self.usage_records[usage_id] = usage_record
        await self._update_aggregated_usage(request.api_key, request.metric_type, request.value, timestamp)
        
        return UsageMeteringResponse(
            usage_id=usage_id,
            api_key=request.api_key,
            endpoint=request.endpoint,
            metric_type=request.metric_type,
            value=request.value,
            cost=cost,
            tier=api_key_tier,
            timestamp=timestamp
        )
    
    async def get_usage_summary(self, api_key: str, start_date: datetime, end_date: datetime) -> Dict:
        filtered_records = [
            record for record in self.usage_records.values()
            if record["api_key"] == api_key and start_date <= record["timestamp"] <= end_date
        ]
        
        summary = {
            "total_requests": 0,
            "total_cost": Decimal("0.00"),
            "breakdown_by_metric": {},
            "breakdown_by_endpoint": {},
            "daily_usage": {}
        }
        
        for record in filtered_records:
            summary["total_requests"] += 1
            summary["total_cost"] += record["cost"]
            
            metric = record["metric_type"]
            if metric not in summary["breakdown_by_metric"]:
                summary["breakdown_by_metric"][metric] = {"count": 0, "value": 0, "cost": Decimal("0.00")}
            summary["breakdown_by_metric"][metric]["count"] += 1
            summary["breakdown_by_metric"][metric]["value"] += record["value"]
            summary["breakdown_by_metric"][metric]["cost"] += record["cost"]
            
            endpoint = record["endpoint"]
            if endpoint not in summary["breakdown_by_endpoint"]:
                summary["breakdown_by_endpoint"][endpoint] = {"count": 0, "cost": Decimal("0.00")}
            summary["breakdown_by_endpoint"][endpoint]["count"] += 1
            summary["breakdown_by_endpoint"][endpoint]["cost"] += record["cost"]
            
            day = record["timestamp"].date().isoformat()
            if day not in summary["daily_usage"]:
                summary["daily_usage"][day] = {"requests": 0, "cost": Decimal("0.00")}
            summary["daily_usage"][day]["requests"] += 1
            summary["daily_usage"][day]["cost"] += record["cost"]
        
        return summary
    
    async def generate_bill(self, request: BillingRequest) -> BillingResponse:
        invoice_id = str(uuid.uuid4())
        
        usage_summary = await self.get_usage_summary(
            request.api_key, 
            request.billing_period_start, 
            request.billing_period_end
        )
        
        developer_id = await self._get_developer_id(request.api_key)
        
        return BillingResponse(
            invoice_id=invoice_id,
            api_key=request.api_key,
            developer_id=developer_id,
            total_amount=usage_summary["total_cost"],
            usage_breakdown=usage_summary["breakdown_by_metric"],
            billing_period={
                "start": request.billing_period_start,
                "end": request.billing_period_end
            },
            due_date=request.billing_period_end + timedelta(days=30),
            status="pending"
        )
    
    async def check_usage_limits(self, api_key: str, metric_type: UsageMetric) -> Dict:
        tier = await self._get_api_key_tier(api_key)
        current_usage = await self._get_current_usage(api_key, metric_type)
        
        limits = {
            PricingTier.FREE: {
                UsageMetric.REQUESTS: 1000,
                UsageMetric.BANDWIDTH: 1000000,  # 1MB
                UsageMetric.STORAGE: 100000000,  # 100MB
                UsageMetric.COMPUTE_TIME: 3600   # 1 hour
            },
            PricingTier.BASIC: {
                UsageMetric.REQUESTS: 10000,
                UsageMetric.BANDWIDTH: 10000000,  # 10MB
                UsageMetric.STORAGE: 1000000000,  # 1GB
                UsageMetric.COMPUTE_TIME: 36000   # 10 hours
            },
            PricingTier.PRO: {
                UsageMetric.REQUESTS: 100000,
                UsageMetric.BANDWIDTH: 100000000,  # 100MB
                UsageMetric.STORAGE: 10000000000,  # 10GB
                UsageMetric.COMPUTE_TIME: 360000   # 100 hours
            },
            PricingTier.ENTERPRISE: {
                UsageMetric.REQUESTS: -1,  # Unlimited
                UsageMetric.BANDWIDTH: -1,
                UsageMetric.STORAGE: -1,
                UsageMetric.COMPUTE_TIME: -1
            }
        }
        
        limit = limits[tier][metric_type]
        
        return {
            "current_usage": current_usage,
            "limit": limit,
            "remaining": limit - current_usage if limit != -1 else -1,
            "percentage_used": (current_usage / limit * 100) if limit > 0 else 0,
            "tier": tier,
            "is_exceeded": current_usage >= limit if limit != -1 else False
        }
    
    def _calculate_cost(self, metric_type: UsageMetric, value: float, tier: PricingTier) -> Decimal:
        unit_price = self.pricing_tiers[tier][metric_type]
        return unit_price * Decimal(str(value))
    
    async def _get_api_key_tier(self, api_key: str) -> PricingTier:
        return PricingTier.BASIC
    
    async def _get_developer_id(self, api_key: str) -> str:
        return f"dev_{api_key[:8]}"
    
    async def _update_aggregated_usage(self, api_key: str, metric_type: UsageMetric, value: float, timestamp: datetime):
        day_key = f"{api_key}:{timestamp.date()}"
        month_key = f"{api_key}:{timestamp.year}-{timestamp.month:02d}"
        
        if day_key not in self.daily_usage:
            self.daily_usage[day_key] = {}
        if metric_type not in self.daily_usage[day_key]:
            self.daily_usage[day_key][metric_type] = 0
        self.daily_usage[day_key][metric_type] += value
        
        if month_key not in self.monthly_usage:
            self.monthly_usage[month_key] = {}
        if metric_type not in self.monthly_usage[month_key]:
            self.monthly_usage[month_key][metric_type] = 0
        self.monthly_usage[month_key][metric_type] += value
    
    async def _get_current_usage(self, api_key: str, metric_type: UsageMetric) -> float:
        today = datetime.now().date()
        day_key = f"{api_key}:{today}"
        
        if day_key in self.daily_usage and metric_type in self.daily_usage[day_key]:
            return self.daily_usage[day_key][metric_type]
        return 0.0

usage_metering_manager = UsageMeteringManager()