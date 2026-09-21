"""
Usage Analytics Dashboard
Comprehensive analytics and reporting for billing and usage data
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import redis
import numpy as np
import pandas as pd
from decimal import Decimal

class ReportType(Enum):
    USAGE_SUMMARY = "usage_summary"
    COST_ANALYSIS = "cost_analysis"
    TREND_ANALYSIS = "trend_analysis"
    COMPARISON = "comparison"
    OPTIMIZATION = "optimization"
    EXECUTIVE_SUMMARY = "executive_summary"

class TimeRange(Enum):
    LAST_HOUR = "last_hour"
    LAST_DAY = "last_day"
    LAST_WEEK = "last_week"
    LAST_MONTH = "last_month"
    LAST_QUARTER = "last_quarter"
    LAST_YEAR = "last_year"
    CUSTOM = "custom"

@dataclass
class AnalyticsQuery:
    """Analytics query parameters"""
    user_id: str
    report_type: ReportType
    time_range: TimeRange
    
    # Time range for custom queries
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Filters
    session_id: Optional[str] = None
    service_type: Optional[str] = None
    
    # Grouping and aggregation
    group_by: List[str] = field(default_factory=list)
    metrics: List[str] = field(default_factory=list)
    
    # Output options
    include_predictions: bool = False
    include_recommendations: bool = False

@dataclass
class AnalyticsResult:
    """Analytics result data"""
    query: AnalyticsQuery
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    charts: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

class UsageAnalyticsDashboard:
    """
    Comprehensive usage analytics and reporting dashboard
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.logger = logging.getLogger(__name__)
        
        # Analytics cache
        self.analytics_cache: Dict[str, AnalyticsResult] = {}
        self.cache_ttl = 1800  # 30 minutes
        
        # Pre-aggregated data
        self.hourly_aggregates: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.daily_aggregates: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.monthly_aggregates: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Performance metrics
        self.metrics = {
            "queries_processed": 0,
            "reports_generated": 0,
            "cache_hits": 0,
            "average_query_time": 0.0
        }

    async def get_dashboard_data(self, user_id: str, period: str = "30d") -> Dict[str, Any]:
        """Get comprehensive dashboard data for user"""
        try:
            start_time = datetime.now()
            
            # Parse time period
            time_range = self._parse_time_period(period)
            
            # Get overview metrics
            overview = await self._get_usage_overview(user_id, time_range)
            
            # Get cost breakdown
            cost_breakdown = await self._get_cost_breakdown(user_id, time_range)
            
            # Get usage trends
            usage_trends = await self._get_usage_trends(user_id, time_range)
            
            # Get top services
            top_services = await self._get_top_services(user_id, time_range)
            
            # Get recent activity
            recent_activity = await self._get_recent_activity(user_id, time_range)
            
            # Get alerts and recommendations
            alerts = await self._get_active_alerts(user_id)
            recommendations = await self._get_optimization_recommendations(user_id)
            
            dashboard_data = {
                "user_id": user_id,
                "period": period,
                "time_range": {
                    "start": time_range["start"].isoformat(),
                    "end": time_range["end"].isoformat()
                },
                "overview": overview,
                "cost_breakdown": cost_breakdown,
                "usage_trends": usage_trends,
                "top_services": top_services,
                "recent_activity": recent_activity,
                "alerts": alerts,
                "recommendations": recommendations,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Update metrics
            query_time = (datetime.now() - start_time).total_seconds()
            self.metrics["average_query_time"] = (
                self.metrics["average_query_time"] * 0.9 + query_time * 0.1
            )
            self.metrics["queries_processed"] += 1
            
            return dashboard_data
            
        except Exception as e:
            self.logger.error(f"Failed to get dashboard data: {e}")
            return {"error": str(e)}

    async def generate_reports(self, user_id: str, report_type: str = "monthly") -> Dict[str, Any]:
        """Generate detailed usage reports"""
        try:
            if report_type == "monthly":
                return await self._generate_monthly_report(user_id)
            elif report_type == "quarterly":
                return await self._generate_quarterly_report(user_id)
            elif report_type == "annual":
                return await self._generate_annual_report(user_id)
            elif report_type == "cost_optimization":
                return await self._generate_cost_optimization_report(user_id)
            else:
                return {"error": f"Unknown report type: {report_type}"}
            
        except Exception as e:
            self.logger.error(f"Report generation failed: {e}")
            return {"error": str(e)}

    async def get_system_trends(self) -> Dict[str, Any]:
        """Get system-wide usage trends"""
        try:
            # Get aggregated system metrics
            system_metrics = await self._get_system_wide_metrics()
            
            # Get growth trends
            growth_trends = await self._calculate_growth_trends()
            
            # Get service popularity
            service_popularity = await self._get_service_popularity()
            
            # Get resource utilization patterns
            resource_patterns = await self._get_resource_utilization_patterns()
            
            return {
                "system_metrics": system_metrics,
                "growth_trends": growth_trends,
                "service_popularity": service_popularity,
                "resource_patterns": resource_patterns,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get system trends: {e}")
            return {"error": str(e)}

    def _parse_time_period(self, period: str) -> Dict[str, datetime]:
        """Parse time period string into start/end dates"""
        end_time = datetime.now(timezone.utc)
        
        if period == "1h":
            start_time = end_time - timedelta(hours=1)
        elif period == "1d":
            start_time = end_time - timedelta(days=1)
        elif period == "7d":
            start_time = end_time - timedelta(days=7)
        elif period == "30d":
            start_time = end_time - timedelta(days=30)
        elif period == "90d":
            start_time = end_time - timedelta(days=90)
        elif period == "1y":
            start_time = end_time - timedelta(days=365)
        else:
            # Default to 30 days
            start_time = end_time - timedelta(days=30)
        
        return {"start": start_time, "end": end_time}

    async def _get_usage_overview(self, user_id: str, time_range: Dict[str, datetime]) -> Dict[str, Any]:
        """Get usage overview metrics"""
        try:
            # Get billing data
            total_cost, session_count = await self._get_cost_and_sessions(user_id, time_range)
            
            # Get resource usage
            resource_usage = await self._get_resource_usage_summary(user_id, time_range)
            
            # Calculate averages
            days_in_period = (time_range["end"] - time_range["start"]).days or 1
            avg_daily_cost = total_cost / days_in_period
            
            return {
                "total_cost": float(total_cost),
                "session_count": session_count,
                "avg_daily_cost": float(avg_daily_cost),
                "total_cpu_hours": resource_usage.get("cpu_hours", 0),
                "total_memory_gb_hours": resource_usage.get("memory_gb_hours", 0),
                "total_storage_gb_hours": resource_usage.get("storage_gb_hours", 0),
                "total_network_gb": resource_usage.get("network_gb", 0),
                "active_days": days_in_period,
                "cost_trend": await self._calculate_cost_trend(user_id, time_range)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get usage overview: {e}")
            return {}

    async def _get_cost_breakdown(self, user_id: str, time_range: Dict[str, datetime]) -> Dict[str, Any]:
        """Get detailed cost breakdown"""
        try:
            cost_breakdown = {
                "by_resource": {
                    "compute": 0.0,
                    "memory": 0.0,
                    "storage": 0.0,
                    "network": 0.0,
                    "other": 0.0
                },
                "by_service": {},
                "by_time": []
            }
            
            if self.redis_client:
                # Get cost data from Redis
                user_sessions_key = f"user_sessions:{user_id}"
                session_ids = await self.redis_client.smembers(user_sessions_key)
                
                for session_id in session_ids:
                    archive_key = f"billing_archive:{user_id}:{session_id}"
                    archive_data = await self.redis_client.hgetall(archive_key)
                    
                    if archive_data and "stopped_at" in archive_data:
                        stopped_at = datetime.fromisoformat(archive_data["stopped_at"])
                        
                        if time_range["start"] <= stopped_at <= time_range["end"]:
                            total_cost = float(archive_data.get("total_cost", 0))
                            service_type = archive_data.get("service_type", "unknown")
                            
                            # Breakdown by service
                            if service_type not in cost_breakdown["by_service"]:
                                cost_breakdown["by_service"][service_type] = 0.0
                            cost_breakdown["by_service"][service_type] += total_cost
                            
                            # Breakdown by resource (simplified)
                            cost_breakdown["by_resource"]["compute"] += total_cost * 0.4
                            cost_breakdown["by_resource"]["memory"] += total_cost * 0.3
                            cost_breakdown["by_resource"]["storage"] += total_cost * 0.2
                            cost_breakdown["by_resource"]["network"] += total_cost * 0.1
                            
                            # Time-based breakdown
                            cost_breakdown["by_time"].append({
                                "date": stopped_at.strftime("%Y-%m-%d"),
                                "cost": total_cost
                            })
            
            return cost_breakdown
            
        except Exception as e:
            self.logger.error(f"Failed to get cost breakdown: {e}")
            return {"by_resource": {}, "by_service": {}, "by_time": []}

    async def _get_usage_trends(self, user_id: str, time_range: Dict[str, datetime]) -> Dict[str, Any]:
        """Get usage trend data"""
        try:
            trends = {
                "cost_over_time": [],
                "usage_over_time": [],
                "resource_trends": {
                    "cpu": [],
                    "memory": [],
                    "storage": [],
                    "network": []
                }
            }
            
            # Generate daily data points
            current_date = time_range["start"]
            while current_date <= time_range["end"]:
                day_cost = await self._get_daily_cost(user_id, current_date)
                day_usage = await self._get_daily_usage(user_id, current_date)
                
                trends["cost_over_time"].append({
                    "date": current_date.strftime("%Y-%m-%d"),
                    "cost": float(day_cost)
                })
                
                trends["usage_over_time"].append({
                    "date": current_date.strftime("%Y-%m-%d"),
                    "sessions": day_usage.get("sessions", 0),
                    "cpu_hours": day_usage.get("cpu_hours", 0),
                    "memory_gb_hours": day_usage.get("memory_gb_hours", 0)
                })
                
                current_date += timedelta(days=1)
            
            return trends
            
        except Exception as e:
            self.logger.error(f"Failed to get usage trends: {e}")
            return {"cost_over_time": [], "usage_over_time": [], "resource_trends": {}}

    async def _get_top_services(self, user_id: str, time_range: Dict[str, datetime]) -> List[Dict[str, Any]]:
        """Get top services by usage and cost"""
        try:
            service_stats = defaultdict(lambda: {"cost": 0.0, "sessions": 0, "usage": 0.0})
            
            if self.redis_client:
                user_sessions_key = f"user_sessions:{user_id}"
                session_ids = await self.redis_client.smembers(user_sessions_key)
                
                for session_id in session_ids:
                    archive_key = f"billing_archive:{user_id}:{session_id}"
                    archive_data = await self.redis_client.hgetall(archive_key)
                    
                    if archive_data:
                        service_type = archive_data.get("service_type", "unknown")
                        cost = float(archive_data.get("total_cost", 0))
                        
                        service_stats[service_type]["cost"] += cost
                        service_stats[service_type]["sessions"] += 1
                        
                        # Add usage data if available
                        usage_data = archive_data.get("resource_usage", "{}")
                        try:
                            usage = json.loads(usage_data)
                            service_stats[service_type]["usage"] += sum(
                                float(v) for v in usage.values() if isinstance(v, (int, float))
                            )
                        except:
                            pass
            
            # Convert to sorted list
            top_services = [
                {
                    "service": service,
                    "cost": stats["cost"],
                    "sessions": stats["sessions"],
                    "usage": stats["usage"],
                    "avg_cost_per_session": stats["cost"] / stats["sessions"] if stats["sessions"] > 0 else 0
                }
                for service, stats in service_stats.items()
            ]
            
            # Sort by cost descending
            top_services.sort(key=lambda x: x["cost"], reverse=True)
            
            return top_services[:10]  # Top 10
            
        except Exception as e:
            self.logger.error(f"Failed to get top services: {e}")
            return []

    async def _get_recent_activity(self, user_id: str, time_range: Dict[str, datetime]) -> List[Dict[str, Any]]:
        """Get recent billing and usage activity"""
        try:
            activities = []
            
            if self.redis_client:
                # Get recent transactions
                transactions_key = f"user_transactions:{user_id}"
                recent_transactions = await self.redis_client.zrevrange(
                    transactions_key, 0, 10, withscores=True
                )
                
                for transaction_id, timestamp in recent_transactions:
                    transaction_key = f"payment_transaction:{transaction_id}"
                    transaction_data = await self.redis_client.hgetall(transaction_key)
                    
                    if transaction_data:
                        activities.append({
                            "type": "payment",
                            "id": transaction_id,
                            "amount": float(transaction_data.get("amount", 0)),
                            "status": transaction_data.get("status", "unknown"),
                            "timestamp": datetime.fromtimestamp(timestamp).isoformat(),
                            "description": transaction_data.get("description", "")
                        })
                
                # Get recent sessions
                user_sessions_key = f"user_sessions:{user_id}"
                session_ids = await self.redis_client.smembers(user_sessions_key)
                
                recent_sessions = []
                for session_id in session_ids:
                    session_key = f"billing_session:{session_id}"
                    session_data = await self.redis_client.hgetall(session_key)
                    
                    if session_data and "started_at" in session_data:
                        started_at = datetime.fromisoformat(session_data["started_at"])
                        recent_sessions.append({
                            "session_id": session_id,
                            "started_at": started_at,
                            "service_type": session_data.get("service_type", "unknown"),
                            "cost": float(session_data.get("accumulated_cost", 0))
                        })
                
                # Sort and add to activities
                recent_sessions.sort(key=lambda x: x["started_at"], reverse=True)
                for session in recent_sessions[:5]:  # Last 5 sessions
                    activities.append({
                        "type": "session",
                        "id": session["session_id"],
                        "service_type": session["service_type"],
                        "cost": session["cost"],
                        "timestamp": session["started_at"].isoformat(),
                        "description": f"Session started for {session['service_type']}"
                    })
            
            # Sort activities by timestamp
            activities.sort(key=lambda x: x["timestamp"], reverse=True)
            
            return activities[:20]  # Last 20 activities
            
        except Exception as e:
            self.logger.error(f"Failed to get recent activity: {e}")
            return []

    async def _get_active_alerts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get active alerts for user (placeholder)"""
        try:
            # This would integrate with the alert system
            # For now, return placeholder data
            return [
                {
                    "alert_id": "alert_1",
                    "type": "cost_threshold",
                    "severity": "medium",
                    "message": "Monthly cost approaching budget limit",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            ]
            
        except Exception as e:
            self.logger.error(f"Failed to get active alerts: {e}")
            return []

    async def _get_optimization_recommendations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get optimization recommendations for user (placeholder)"""
        try:
            # This would integrate with the cost prediction engine
            # For now, return placeholder data
            return [
                {
                    "recommendation_id": "rec_1",
                    "type": "scaling_optimization",
                    "description": "Enable auto-scaling to reduce costs during low usage periods",
                    "potential_savings": 25.00,
                    "confidence": 0.85
                }
            ]
            
        except Exception as e:
            self.logger.error(f"Failed to get optimization recommendations: {e}")
            return []

    async def _get_cost_and_sessions(self, user_id: str, time_range: Dict[str, datetime]) -> Tuple[Decimal, int]:
        """Get total cost and session count for time range"""
        try:
            total_cost = Decimal("0.00")
            session_count = 0
            
            if self.redis_client:
                user_sessions_key = f"user_sessions:{user_id}"
                session_ids = await self.redis_client.smembers(user_sessions_key)
                
                for session_id in session_ids:
                    archive_key = f"billing_archive:{user_id}:{session_id}"
                    archive_data = await self.redis_client.hgetall(archive_key)
                    
                    if archive_data and "stopped_at" in archive_data:
                        stopped_at = datetime.fromisoformat(archive_data["stopped_at"])
                        
                        if time_range["start"] <= stopped_at <= time_range["end"]:
                            cost = Decimal(archive_data.get("total_cost", "0.00"))
                            total_cost += cost
                            session_count += 1
            
            return total_cost, session_count
            
        except Exception as e:
            self.logger.error(f"Failed to get cost and sessions: {e}")
            return Decimal("0.00"), 0

    async def _get_resource_usage_summary(self, user_id: str, time_range: Dict[str, datetime]) -> Dict[str, float]:
        """Get aggregated resource usage summary"""
        try:
            usage_summary = {
                "cpu_hours": 0.0,
                "memory_gb_hours": 0.0,
                "storage_gb_hours": 0.0,
                "network_gb": 0.0
            }
            
            if self.redis_client:
                user_sessions_key = f"user_sessions:{user_id}"
                session_ids = await self.redis_client.smembers(user_sessions_key)
                
                for session_id in session_ids:
                    archive_key = f"billing_archive:{user_id}:{session_id}"
                    archive_data = await self.redis_client.hgetall(archive_key)
                    
                    if archive_data:
                        usage_data = archive_data.get("resource_usage", "{}")
                        try:
                            usage = json.loads(usage_data)
                            usage_summary["cpu_hours"] += usage.get("cpu_seconds", 0) / 3600
                            usage_summary["memory_gb_hours"] += usage.get("memory_mb_seconds", 0) / (1024 * 3600)
                            usage_summary["storage_gb_hours"] += usage.get("storage_gb_seconds", 0) / 3600
                            usage_summary["network_gb"] += usage.get("network_gb", 0)
                        except:
                            pass
            
            return usage_summary
            
        except Exception as e:
            self.logger.error(f"Failed to get resource usage summary: {e}")
            return {"cpu_hours": 0.0, "memory_gb_hours": 0.0, "storage_gb_hours": 0.0, "network_gb": 0.0}

    async def _calculate_cost_trend(self, user_id: str, time_range: Dict[str, datetime]) -> str:
        """Calculate cost trend (up/down/stable)"""
        try:
            # Get costs for first and second half of period
            mid_point = time_range["start"] + (time_range["end"] - time_range["start"]) / 2
            
            first_half_cost, _ = await self._get_cost_and_sessions(
                user_id, {"start": time_range["start"], "end": mid_point}
            )
            second_half_cost, _ = await self._get_cost_and_sessions(
                user_id, {"start": mid_point, "end": time_range["end"]}
            )
            
            if first_half_cost == 0:
                return "stable"
            
            change_percent = float((second_half_cost - first_half_cost) / first_half_cost * 100)
            
            if change_percent > 10:
                return "increasing"
            elif change_percent < -10:
                return "decreasing"
            else:
                return "stable"
            
        except Exception as e:
            self.logger.error(f"Failed to calculate cost trend: {e}")
            return "stable"

    async def _get_daily_cost(self, user_id: str, date: datetime) -> Decimal:
        """Get cost for a specific day"""
        try:
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            cost, _ = await self._get_cost_and_sessions(user_id, {"start": day_start, "end": day_end})
            return cost
            
        except Exception as e:
            self.logger.error(f"Failed to get daily cost: {e}")
            return Decimal("0.00")

    async def _get_daily_usage(self, user_id: str, date: datetime) -> Dict[str, Any]:
        """Get usage for a specific day"""
        try:
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            _, sessions = await self._get_cost_and_sessions(user_id, {"start": day_start, "end": day_end})
            usage_summary = await self._get_resource_usage_summary(user_id, {"start": day_start, "end": day_end})
            
            return {
                "sessions": sessions,
                "cpu_hours": usage_summary.get("cpu_hours", 0),
                "memory_gb_hours": usage_summary.get("memory_gb_hours", 0)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get daily usage: {e}")
            return {"sessions": 0, "cpu_hours": 0, "memory_gb_hours": 0}

    async def _generate_monthly_report(self, user_id: str) -> Dict[str, Any]:
        """Generate monthly usage report"""
        try:
            # Get current month data
            now = datetime.now(timezone.utc)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
            
            time_range = {"start": month_start, "end": min(month_end, now)}
            
            # Get comprehensive data
            overview = await self._get_usage_overview(user_id, time_range)
            cost_breakdown = await self._get_cost_breakdown(user_id, time_range)
            trends = await self._get_usage_trends(user_id, time_range)
            top_services = await self._get_top_services(user_id, time_range)
            
            # Generate insights
            insights = await self._generate_monthly_insights(user_id, overview, trends)
            
            report = {
                "report_type": "monthly",
                "user_id": user_id,
                "period": {
                    "start": month_start.isoformat(),
                    "end": time_range["end"].isoformat(),
                    "month": month_start.strftime("%B %Y")
                },
                "executive_summary": {
                    "total_cost": overview.get("total_cost", 0),
                    "total_sessions": overview.get("session_count", 0),
                    "avg_daily_cost": overview.get("avg_daily_cost", 0),
                    "cost_trend": overview.get("cost_trend", "stable")
                },
                "detailed_breakdown": {
                    "overview": overview,
                    "cost_breakdown": cost_breakdown,
                    "usage_trends": trends,
                    "top_services": top_services
                },
                "insights": insights,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            self.metrics["reports_generated"] += 1
            
            return report
            
        except Exception as e:
            self.logger.error(f"Monthly report generation failed: {e}")
            return {"error": str(e)}

    async def _generate_quarterly_report(self, user_id: str) -> Dict[str, Any]:
        """Generate quarterly usage report"""
        try:
            # Get current quarter data
            now = datetime.now(timezone.utc)
            quarter_start = datetime(now.year, ((now.month - 1) // 3) * 3 + 1, 1, tzinfo=timezone.utc)
            quarter_end = (quarter_start + timedelta(days=92)).replace(day=1) - timedelta(seconds=1)
            
            time_range = {"start": quarter_start, "end": min(quarter_end, now)}
            
            # Get comprehensive data
            overview = await self._get_usage_overview(user_id, time_range)
            cost_breakdown = await self._get_cost_breakdown(user_id, time_range)
            trends = await self._get_usage_trends(user_id, time_range)
            
            # Generate quarterly insights
            insights = await self._generate_quarterly_insights(user_id, overview, trends)
            
            report = {
                "report_type": "quarterly",
                "user_id": user_id,
                "period": {
                    "start": quarter_start.isoformat(),
                    "end": time_range["end"].isoformat(),
                    "quarter": f"Q{((now.month - 1) // 3) + 1} {now.year}"
                },
                "executive_summary": {
                    "total_cost": overview.get("total_cost", 0),
                    "total_sessions": overview.get("session_count", 0),
                    "avg_monthly_cost": overview.get("total_cost", 0) / 3,  # Quarterly average
                    "cost_trend": overview.get("cost_trend", "stable")
                },
                "detailed_analysis": {
                    "overview": overview,
                    "cost_breakdown": cost_breakdown,
                    "usage_trends": trends
                },
                "insights": insights,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Quarterly report generation failed: {e}")
            return {"error": str(e)}

    async def _generate_annual_report(self, user_id: str) -> Dict[str, Any]:
        """Generate annual usage report"""
        try:
            # Get current year data
            now = datetime.now(timezone.utc)
            year_start = datetime(now.year, 1, 1, tzinfo=timezone.utc)
            year_end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
            
            time_range = {"start": year_start, "end": min(year_end, now)}
            
            # Get comprehensive data
            overview = await self._get_usage_overview(user_id, time_range)
            cost_breakdown = await self._get_cost_breakdown(user_id, time_range)
            
            # Generate annual insights
            insights = await self._generate_annual_insights(user_id, overview)
            
            report = {
                "report_type": "annual",
                "user_id": user_id,
                "period": {
                    "start": year_start.isoformat(),
                    "end": time_range["end"].isoformat(),
                    "year": now.year
                },
                "executive_summary": {
                    "total_cost": overview.get("total_cost", 0),
                    "avg_monthly_cost": overview.get("total_cost", 0) / 12,
                    "total_sessions": overview.get("session_count", 0),
                    "cost_trend": overview.get("cost_trend", "stable")
                },
                "annual_analysis": {
                    "overview": overview,
                    "cost_breakdown": cost_breakdown
                },
                "insights": insights,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Annual report generation failed: {e}")
            return {"error": str(e)}

    async def _generate_cost_optimization_report(self, user_id: str) -> Dict[str, Any]:
        """Generate cost optimization report"""
        try:
            # Get last 30 days data
            time_range = self._parse_time_period("30d")
            
            # Get usage patterns
            overview = await self._get_usage_overview(user_id, time_range)
            cost_breakdown = await self._get_cost_breakdown(user_id, time_range)
            
            # Generate optimization recommendations
            recommendations = []
            
            # Low utilization recommendations
            if overview.get("total_cost", 0) > 50 and overview.get("avg_daily_cost", 0) < 2:
                recommendations.append({
                    "type": "right_sizing",
                    "description": "Consider downsizing resources based on low average usage",
                    "potential_savings": overview.get("total_cost", 0) * 0.25,
                    "confidence": 0.8
                })
            
            # Service consolidation
            service_count = len(cost_breakdown.get("by_service", {}))
            if service_count > 3:
                recommendations.append({
                    "type": "consolidation",
                    "description": "Consolidate services to reduce management overhead",
                    "potential_savings": overview.get("total_cost", 0) * 0.15,
                    "confidence": 0.6
                })
            
            total_potential_savings = sum(rec["potential_savings"] for rec in recommendations)
            
            report = {
                "report_type": "cost_optimization",
                "user_id": user_id,
                "analysis_period": time_range,
                "current_spending": {
                    "total_cost": overview.get("total_cost", 0),
                    "avg_daily_cost": overview.get("avg_daily_cost", 0),
                    "cost_breakdown": cost_breakdown["by_resource"]
                },
                "optimization_opportunities": {
                    "total_potential_savings": total_potential_savings,
                    "savings_percentage": (total_potential_savings / max(overview.get("total_cost", 1), 1)) * 100,
                    "recommendations": recommendations
                },
                "next_steps": [
                    "Review resource utilization patterns",
                    "Implement recommended optimizations",
                    "Monitor savings after implementation"
                ],
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Cost optimization report generation failed: {e}")
            return {"error": str(e)}

    async def _generate_monthly_insights(
        self,
        user_id: str,
        overview: Dict[str, Any],
        trends: Dict[str, Any]
    ) -> List[str]:
        """Generate monthly insights"""
        insights = []
        
        try:
            # Cost trend insights
            if overview.get("cost_trend") == "increasing":
                insights.append("Your costs are trending upward this month. Consider reviewing your usage patterns.")
            elif overview.get("cost_trend") == "decreasing":
                insights.append("Great job! Your costs are trending downward this month.")
            
            # Usage efficiency
            avg_cost = overview.get("avg_daily_cost", 0)
            if avg_cost > 0:
                insights.append(f"Your average daily cost is ${avg_cost:.2f}.")
            
            # Session insights
            session_count = overview.get("session_count", 0)
            if session_count > 50:
                insights.append("High session activity detected. Consider optimizing for cost efficiency.")
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Failed to generate monthly insights: {e}")
            return ["Unable to generate insights at this time."]

    async def _generate_quarterly_insights(
        self,
        user_id: str,
        overview: Dict[str, Any],
        trends: Dict[str, Any]
    ) -> List[str]:
        """Generate quarterly insights"""
        insights = []
        
        try:
            total_cost = overview.get("total_cost", 0)
            if total_cost > 500:
                insights.append("Quarterly spending exceeds $500. Consider implementing cost controls.")
            
            insights.append("Quarterly analysis shows consistent usage patterns.")
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Failed to generate quarterly insights: {e}")
            return ["Unable to generate insights at this time."]

    async def _generate_annual_insights(
        self,
        user_id: str,
        overview: Dict[str, Any]
    ) -> List[str]:
        """Generate annual insights"""
        insights = []
        
        try:
            total_cost = overview.get("total_cost", 0)
            insights.append(f"Annual spending: ${total_cost:.2f}")
            
            if total_cost > 1000:
                insights.append("Consider enterprise tier for better rates.")
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Failed to generate annual insights: {e}")
            return ["Unable to generate insights at this time."]

    async def _get_system_wide_metrics(self) -> Dict[str, Any]:
        """Get system-wide metrics"""
        return {
            "total_users": 1000,  # Placeholder
            "total_sessions": 5000,
            "total_revenue": 25000.0,
            "average_session_cost": 5.0
        }

    async def _calculate_growth_trends(self) -> Dict[str, Any]:
        """Calculate growth trends"""
        return {
            "user_growth": 15.5,  # Placeholder
            "revenue_growth": 22.3,
            "usage_growth": 18.7
        }

    async def _get_service_popularity(self) -> List[Dict[str, Any]]:
        """Get service popularity rankings"""
        return [
            {"service": "web_hosting", "usage_percentage": 35.5},
            {"service": "database", "usage_percentage": 25.2},
            {"service": "analytics", "usage_percentage": 20.1}
        ]

    async def _get_resource_utilization_patterns(self) -> Dict[str, Any]:
        """Get resource utilization patterns"""
        return {
            "peak_hours": [9, 10, 11, 14, 15, 16],
            "low_usage_hours": [0, 1, 2, 3, 4, 5],
            "weekend_vs_weekday": {"weekday": 0.85, "weekend": 0.45}
        }

    async def get_status(self) -> Dict[str, Any]:
        """Get analytics dashboard status"""
        return {
            "cached_reports": len(self.analytics_cache),
            "metrics": self.metrics,
            "aggregation_status": {
                "hourly_aggregates": len(self.hourly_aggregates),
                "daily_aggregates": len(self.daily_aggregates),
                "monthly_aggregates": len(self.monthly_aggregates)
            },
            "redis_connected": self.redis_client is not None
        }

    async def shutdown(self):
        """Shutdown analytics dashboard"""
        try:
            self.logger.info("Shutting down usage analytics dashboard...")
            
            # Clear caches
            self.analytics_cache.clear()
            
            self.logger.info("Usage analytics dashboard shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during analytics dashboard shutdown: {e}")