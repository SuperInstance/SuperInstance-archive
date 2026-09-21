import asyncio
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, Counter
import statistics
from models.monetization_models import *

class UsageAnalyticsManager:
    def __init__(self):
        self.analytics_data = {}
        self.cached_reports = {}
        self.real_time_metrics = {}
        self.anomaly_alerts = {}
        self.custom_dashboards = {}
        
    async def generate_usage_analytics(self, request: UsageAnalyticsRequest) -> UsageAnalyticsResponse:
        from core.usage_metering import usage_metering_manager
        from core.api_key_management import api_key_manager
        
        if request.api_key:
            usage_data = await self._get_api_key_usage_data(
                request.api_key, request.start_date, request.end_date
            )
        elif request.provider_id:
            usage_data = await self._get_provider_usage_data(
                request.provider_id, request.start_date, request.end_date
            )
        else:
            usage_data = await self._get_global_usage_data(
                request.start_date, request.end_date
            )
        
        analytics = await self._process_analytics_data(
            usage_data, request.metric_types, request.group_by
        )
        
        return UsageAnalyticsResponse(
            total_requests=analytics["total_requests"],
            total_revenue=analytics["total_revenue"],
            top_endpoints=analytics["top_endpoints"],
            usage_trends=analytics["usage_trends"],
            geographic_distribution=analytics["geographic_distribution"],
            error_rates=analytics["error_rates"],
            response_times=analytics["response_times"],
            tier_distribution=analytics["tier_distribution"]
        )
    
    async def create_real_time_dashboard(self, dashboard_id: str, config: Dict) -> Dict:
        dashboard = {
            "dashboard_id": dashboard_id,
            "config": config,
            "created_at": datetime.now(),
            "last_updated": datetime.now(),
            "widgets": config.get("widgets", []),
            "refresh_interval": config.get("refresh_interval", 60),
            "filters": config.get("filters", {}),
            "sharing_settings": config.get("sharing_settings", {"private": True})
        }
        
        self.custom_dashboards[dashboard_id] = dashboard
        
        return {
            "success": True,
            "dashboard_id": dashboard_id,
            "message": "Real-time dashboard created",
            "dashboard_url": f"/analytics/dashboard/{dashboard_id}"
        }
    
    async def get_real_time_metrics(self, metric_types: List[str] = None) -> Dict:
        now = datetime.now()
        last_hour = now - timedelta(hours=1)
        last_24h = now - timedelta(hours=24)
        
        if not metric_types:
            metric_types = ["requests", "revenue", "errors", "response_time"]
        
        metrics = {}
        
        if "requests" in metric_types:
            metrics["requests"] = {
                "last_hour": await self._count_requests_in_period(last_hour, now),
                "last_24h": await self._count_requests_in_period(last_24h, now),
                "rate_per_minute": await self._calculate_request_rate(),
                "trend": await self._calculate_trend("requests", 24)
            }
        
        if "revenue" in metric_types:
            metrics["revenue"] = {
                "last_hour": await self._calculate_revenue_in_period(last_hour, now),
                "last_24h": await self._calculate_revenue_in_period(last_24h, now),
                "rate_per_hour": await self._calculate_revenue_rate(),
                "trend": await self._calculate_trend("revenue", 24)
            }
        
        if "errors" in metric_types:
            metrics["errors"] = {
                "last_hour": await self._count_errors_in_period(last_hour, now),
                "error_rate": await self._calculate_error_rate(),
                "top_error_codes": await self._get_top_error_codes(),
                "trend": await self._calculate_trend("errors", 24)
            }
        
        if "response_time" in metric_types:
            metrics["response_time"] = {
                "average": await self._calculate_average_response_time(),
                "p95": await self._calculate_percentile_response_time(95),
                "p99": await self._calculate_percentile_response_time(99),
                "trend": await self._calculate_trend("response_time", 24)
            }
        
        return {
            "timestamp": now,
            "metrics": metrics,
            "active_apis": await self._count_active_apis(),
            "active_developers": await self._count_active_developers()
        }
    
    async def generate_custom_report(self, report_config: Dict) -> Dict:
        report_id = str(uuid.uuid4())
        
        start_date = datetime.fromisoformat(report_config["start_date"])
        end_date = datetime.fromisoformat(report_config["end_date"])
        filters = report_config.get("filters", {})
        metrics = report_config.get("metrics", ["requests", "revenue", "errors"])
        
        report_data = await self._generate_filtered_report(
            start_date, end_date, filters, metrics
        )
        
        report = {
            "report_id": report_id,
            "generated_at": datetime.now(),
            "config": report_config,
            "data": report_data,
            "summary": await self._generate_report_summary(report_data),
            "charts": await self._generate_chart_data(report_data, report_config.get("charts", []))
        }
        
        self.cached_reports[report_id] = report
        
        return report
    
    async def detect_usage_anomalies(self, api_key: str = None, 
                                   threshold_multiplier: float = 3.0) -> List[Dict]:
        
        anomalies = []
        now = datetime.now()
        
        if api_key:
            usage_patterns = await self._analyze_api_key_patterns(api_key)
        else:
            usage_patterns = await self._analyze_global_patterns()
        
        for pattern_name, pattern_data in usage_patterns.items():
            current_value = pattern_data["current"]
            historical_mean = pattern_data["historical_mean"]
            historical_std = pattern_data["historical_std"]
            
            threshold = historical_mean + (threshold_multiplier * historical_std)
            
            if current_value > threshold:
                anomaly_id = str(uuid.uuid4())
                
                anomaly = {
                    "anomaly_id": anomaly_id,
                    "type": "spike",
                    "metric": pattern_name,
                    "api_key": api_key,
                    "current_value": current_value,
                    "expected_value": historical_mean,
                    "threshold": threshold,
                    "severity": "high" if current_value > threshold * 1.5 else "medium",
                    "detected_at": now,
                    "confidence": min(95, abs(current_value - historical_mean) / historical_std * 10)
                }
                
                anomalies.append(anomaly)
                self.anomaly_alerts[anomaly_id] = anomaly
        
        return anomalies
    
    async def get_usage_forecasting(self, api_key: str = None, 
                                  forecast_days: int = 30) -> Dict:
        
        historical_data = await self._get_historical_usage_data(api_key, days=90)
        
        forecast = {
            "forecast_period_days": forecast_days,
            "generated_at": datetime.now(),
            "confidence_level": 0.85,
            "predictions": {}
        }
        
        metrics = ["requests", "revenue", "bandwidth"]
        
        for metric in metrics:
            metric_data = [point[metric] for point in historical_data if metric in point]
            
            if len(metric_data) >= 7:
                trend = await self._calculate_linear_trend(metric_data)
                seasonal_factor = await self._calculate_seasonal_factor(metric_data)
                
                predictions = []
                base_value = metric_data[-1] if metric_data else 0
                
                for day in range(1, forecast_days + 1):
                    predicted_value = base_value + (trend * day) * seasonal_factor
                    predictions.append({
                        "date": (datetime.now() + timedelta(days=day)).date().isoformat(),
                        "predicted_value": max(0, predicted_value),
                        "confidence_interval": {
                            "lower": predicted_value * 0.85,
                            "upper": predicted_value * 1.15
                        }
                    })
                
                forecast["predictions"][metric] = predictions
        
        return forecast
    
    async def generate_cost_optimization_insights(self, api_key: str = None) -> Dict:
        usage_data = await self._get_detailed_usage_data(api_key)
        
        insights = []
        potential_savings = Decimal("0.00")
        
        underutilized_tiers = await self._identify_underutilized_tiers(usage_data)
        for tier_insight in underutilized_tiers:
            insights.append(tier_insight)
            potential_savings += tier_insight.get("potential_monthly_savings", Decimal("0.00"))
        
        high_cost_endpoints = await self._identify_high_cost_endpoints(usage_data)
        for endpoint_insight in high_cost_endpoints:
            insights.append(endpoint_insight)
        
        inefficient_patterns = await self._identify_inefficient_usage_patterns(usage_data)
        for pattern_insight in inefficient_patterns:
            insights.append(pattern_insight)
            potential_savings += pattern_insight.get("potential_monthly_savings", Decimal("0.00"))
        
        return {
            "optimization_insights": insights,
            "total_potential_monthly_savings": potential_savings,
            "current_monthly_cost": await self._calculate_current_monthly_cost(api_key),
            "optimization_score": await self._calculate_optimization_score(usage_data),
            "recommendations": await self._generate_optimization_recommendations(insights)
        }
    
    async def export_analytics_data(self, request: UsageAnalyticsRequest, 
                                  export_format: str = "json") -> Dict:
        
        analytics = await self.generate_usage_analytics(request)
        
        export_id = str(uuid.uuid4())
        export_data = {
            "export_id": export_id,
            "format": export_format,
            "generated_at": datetime.now(),
            "request_params": request.dict(),
            "data": analytics.dict()
        }
        
        if export_format == "csv":
            csv_data = await self._convert_to_csv(analytics)
            export_data["csv_content"] = csv_data
        elif export_format == "xlsx":
            xlsx_data = await self._convert_to_xlsx(analytics)
            export_data["xlsx_content"] = xlsx_data
        
        return {
            "export_id": export_id,
            "download_url": f"/analytics/export/{export_id}",
            "format": export_format,
            "size_bytes": len(str(export_data)),
            "expires_at": datetime.now() + timedelta(hours=24)
        }
    
    async def _get_api_key_usage_data(self, api_key: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        from core.usage_metering import usage_metering_manager
        
        return [
            {
                "timestamp": datetime.now() - timedelta(hours=i),
                "requests": 100 + (i * 5),
                "revenue": Decimal("10.50") + (Decimal("0.50") * i),
                "errors": 2 + (i % 3),
                "response_time": 150 + (i * 2),
                "endpoint": f"/api/v1/endpoint{i % 5}",
                "geographic_region": ["us-east", "eu-west", "asia-pacific"][i % 3]
            }
            for i in range(24)
        ]
    
    async def _get_provider_usage_data(self, provider_id: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        return []
    
    async def _get_global_usage_data(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        return []
    
    async def _process_analytics_data(self, usage_data: List[Dict], 
                                    metric_types: Optional[List[UsageMetric]], 
                                    group_by: Optional[str]) -> Dict:
        
        total_requests = sum(point.get("requests", 0) for point in usage_data)
        total_revenue = sum(point.get("revenue", Decimal("0.00")) for point in usage_data)
        
        endpoint_stats = defaultdict(lambda: {"requests": 0, "revenue": Decimal("0.00")})
        for point in usage_data:
            endpoint = point.get("endpoint", "unknown")
            endpoint_stats[endpoint]["requests"] += point.get("requests", 0)
            endpoint_stats[endpoint]["revenue"] += point.get("revenue", Decimal("0.00"))
        
        top_endpoints = [
            {"endpoint": endpoint, "requests": stats["requests"], "revenue": float(stats["revenue"])}
            for endpoint, stats in sorted(
                endpoint_stats.items(),
                key=lambda x: x[1]["requests"],
                reverse=True
            )[:10]
        ]
        
        usage_trends = [
            {
                "timestamp": point["timestamp"].isoformat(),
                "requests": point.get("requests", 0),
                "revenue": float(point.get("revenue", Decimal("0.00")))
            }
            for point in usage_data[-24:]
        ]
        
        geographic_distribution = Counter(point.get("geographic_region", "unknown") for point in usage_data)
        
        error_rates = {
            "total_errors": sum(point.get("errors", 0) for point in usage_data),
            "error_rate_percentage": (sum(point.get("errors", 0) for point in usage_data) / total_requests * 100) if total_requests > 0 else 0
        }
        
        response_times = {}
        if usage_data:
            response_time_values = [point.get("response_time", 0) for point in usage_data if point.get("response_time")]
            if response_time_values:
                response_times = {
                    "average": statistics.mean(response_time_values),
                    "median": statistics.median(response_time_values),
                    "p95": sorted(response_time_values)[int(len(response_time_values) * 0.95)] if response_time_values else 0
                }
        
        tier_distribution = {"free": 25, "basic": 45, "pro": 25, "enterprise": 5}
        
        return {
            "total_requests": total_requests,
            "total_revenue": total_revenue,
            "top_endpoints": top_endpoints,
            "usage_trends": usage_trends,
            "geographic_distribution": dict(geographic_distribution),
            "error_rates": error_rates,
            "response_times": response_times,
            "tier_distribution": tier_distribution
        }
    
    async def _count_requests_in_period(self, start: datetime, end: datetime) -> int:
        return 1500
    
    async def _calculate_revenue_in_period(self, start: datetime, end: datetime) -> Decimal:
        return Decimal("1250.75")
    
    async def _calculate_request_rate(self) -> float:
        return 25.5
    
    async def _calculate_revenue_rate(self) -> Decimal:
        return Decimal("52.20")
    
    async def _count_errors_in_period(self, start: datetime, end: datetime) -> int:
        return 15
    
    async def _calculate_error_rate(self) -> float:
        return 1.2
    
    async def _get_top_error_codes(self) -> List[Dict]:
        return [
            {"code": 429, "count": 8, "percentage": 53.3},
            {"code": 500, "count": 4, "percentage": 26.7},
            {"code": 401, "count": 3, "percentage": 20.0}
        ]
    
    async def _calculate_average_response_time(self) -> float:
        return 145.2
    
    async def _calculate_percentile_response_time(self, percentile: int) -> float:
        return 200.0 if percentile == 95 else 350.0
    
    async def _calculate_trend(self, metric: str, hours: int) -> str:
        return "increasing"
    
    async def _count_active_apis(self) -> int:
        return 127
    
    async def _count_active_developers(self) -> int:
        return 456
    
    async def _generate_filtered_report(self, start_date: datetime, end_date: datetime,
                                      filters: Dict, metrics: List[str]) -> Dict:
        return {"filtered_data": "placeholder"}
    
    async def _generate_report_summary(self, report_data: Dict) -> Dict:
        return {"summary": "placeholder"}
    
    async def _generate_chart_data(self, report_data: Dict, charts: List[str]) -> Dict:
        return {"charts": "placeholder"}
    
    async def _analyze_api_key_patterns(self, api_key: str) -> Dict:
        return {
            "request_volume": {
                "current": 1500,
                "historical_mean": 1000,
                "historical_std": 200
            }
        }
    
    async def _analyze_global_patterns(self) -> Dict:
        return {}
    
    async def _get_historical_usage_data(self, api_key: str, days: int) -> List[Dict]:
        return []
    
    async def _calculate_linear_trend(self, data: List[float]) -> float:
        return 1.05
    
    async def _calculate_seasonal_factor(self, data: List[float]) -> float:
        return 1.0
    
    async def _get_detailed_usage_data(self, api_key: str) -> Dict:
        return {}
    
    async def _identify_underutilized_tiers(self, usage_data: Dict) -> List[Dict]:
        return []
    
    async def _identify_high_cost_endpoints(self, usage_data: Dict) -> List[Dict]:
        return []
    
    async def _identify_inefficient_usage_patterns(self, usage_data: Dict) -> List[Dict]:
        return []
    
    async def _calculate_current_monthly_cost(self, api_key: str) -> Decimal:
        return Decimal("150.00")
    
    async def _calculate_optimization_score(self, usage_data: Dict) -> float:
        return 75.5
    
    async def _generate_optimization_recommendations(self, insights: List[Dict]) -> List[str]:
        return [
            "Consider upgrading to Pro tier for better per-request pricing",
            "Implement request caching to reduce API calls by 25%",
            "Optimize high-frequency endpoints for better performance"
        ]
    
    async def _convert_to_csv(self, analytics: UsageAnalyticsResponse) -> str:
        return "CSV content placeholder"
    
    async def _convert_to_xlsx(self, analytics: UsageAnalyticsResponse) -> bytes:
        return b"XLSX content placeholder"

usage_analytics_manager = UsageAnalyticsManager()