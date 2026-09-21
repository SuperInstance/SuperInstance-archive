#!/usr/bin/env python3
"""
Data Insights and Analytics Engine for ActiveLog
Advanced analytics and insight generation from user data patterns
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from collections import defaultdict, Counter
from pathlib import Path
import numpy as np
from enum import Enum
import statistics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InsightType(Enum):
    """Types of insights that can be generated"""
    USAGE_PATTERN = "usage_pattern"
    CONTENT_TREND = "content_trend"
    PRODUCTIVITY = "productivity"
    HEALTH_FITNESS = "health_fitness"
    FINANCIAL = "financial"
    SOCIAL = "social"
    TIME_MANAGEMENT = "time_management"
    LOCATION_PATTERN = "location_pattern"
    CONTENT_QUALITY = "content_quality"
    STORAGE_OPTIMIZATION = "storage_optimization"

class InsightPriority(Enum):
    """Priority levels for insights"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

@dataclass
class Insight:
    """Represents a generated insight"""
    insight_id: str
    user_id: str
    insight_type: InsightType
    title: str
    description: str
    confidence: float
    priority: InsightPriority
    data: Dict[str, Any]
    visualization_data: Optional[Dict[str, Any]] = None
    action_suggestions: List[str] = None
    created_at: datetime = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None

@dataclass
class AnalyticsReport:
    """Comprehensive analytics report"""
    report_id: str
    user_id: str
    report_type: str
    time_period: Dict[str, datetime]
    insights: List[Insight]
    summary_statistics: Dict[str, Any]
    trends: Dict[str, Any]
    recommendations: List[str]
    generated_at: datetime

class DataAnalytics:
    """Core analytics engine for data pattern analysis"""
    
    def __init__(self):
        self.insight_generators = {}
        self._register_insight_generators()
    
    def _register_insight_generators(self):
        """Register insight generation methods"""
        self.insight_generators = {
            InsightType.USAGE_PATTERN: self._generate_usage_insights,
            InsightType.CONTENT_TREND: self._generate_content_insights,
            InsightType.PRODUCTIVITY: self._generate_productivity_insights,
            InsightType.TIME_MANAGEMENT: self._generate_time_insights,
            InsightType.LOCATION_PATTERN: self._generate_location_insights,
            InsightType.STORAGE_OPTIMIZATION: self._generate_storage_insights,
            InsightType.CONTENT_QUALITY: self._generate_quality_insights
        }
    
    async def analyze_user_data(self, user_id: str, data_items: List[Dict[str, Any]], 
                               time_period: Dict[str, datetime] = None) -> AnalyticsReport:
        """Generate comprehensive analytics report for user data"""
        if not time_period:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=30)
            time_period = {"start": start_date, "end": end_date}
        
        # Generate insights
        insights = []
        for insight_type, generator in self.insight_generators.items():
            try:
                type_insights = await generator(user_id, data_items, time_period)
                insights.extend(type_insights)
            except Exception as e:
                logger.error(f"Error generating {insight_type.value} insights: {str(e)}")
        
        # Generate summary statistics
        summary_stats = await self._generate_summary_statistics(data_items, time_period)
        
        # Generate trends
        trends = await self._generate_trends(data_items, time_period)
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(insights, summary_stats, trends)
        
        # Create report
        report = AnalyticsReport(
            report_id=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            user_id=user_id,
            report_type="comprehensive",
            time_period=time_period,
            insights=insights,
            summary_statistics=summary_stats,
            trends=trends,
            recommendations=recommendations,
            generated_at=datetime.now(timezone.utc)
        )
        
        return report
    
    async def _generate_usage_insights(self, user_id: str, data_items: List[Dict[str, Any]], 
                                     time_period: Dict[str, datetime]) -> List[Insight]:
        """Generate usage pattern insights"""
        insights = []
        
        # Analyze activity by time of day
        hourly_activity = defaultdict(int)
        daily_activity = defaultdict(int)
        
        for item in data_items:
            created_at = item.get('created_at')
            if created_at:
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                hour = created_at.hour
                day = created_at.strftime('%A')
                
                hourly_activity[hour] += 1
                daily_activity[day] += 1
        
        # Peak activity hours
        if hourly_activity:
            peak_hour = max(hourly_activity.items(), key=lambda x: x[1])
            
            insights.append(Insight(
                insight_id=f"usage_peak_hour_{user_id}",
                user_id=user_id,
                insight_type=InsightType.USAGE_PATTERN,
                title="Peak Activity Time",
                description=f"You're most active at {peak_hour[0]:02d}:00 with {peak_hour[1]} activities",
                confidence=0.85,
                priority=InsightPriority.MEDIUM,
                data={
                    "peak_hour": peak_hour[0],
                    "activity_count": peak_hour[1],
                    "hourly_distribution": dict(hourly_activity)
                },
                visualization_data={
                    "chart_type": "bar",
                    "x_axis": list(range(24)),
                    "y_axis": [hourly_activity.get(h, 0) for h in range(24)],
                    "title": "Activity by Hour of Day"
                },
                action_suggestions=[
                    "Schedule important tasks during your peak activity time",
                    "Use quiet hours for focused work or rest"
                ],
                created_at=datetime.now(timezone.utc)
            ))
        
        # Most active day
        if daily_activity:
            peak_day = max(daily_activity.items(), key=lambda x: x[1])
            
            insights.append(Insight(
                insight_id=f"usage_peak_day_{user_id}",
                user_id=user_id,
                insight_type=InsightType.USAGE_PATTERN,
                title="Most Active Day",
                description=f"{peak_day[0]} is your most active day with {peak_day[1]} activities",
                confidence=0.8,
                priority=InsightPriority.LOW,
                data={
                    "peak_day": peak_day[0],
                    "activity_count": peak_day[1],
                    "daily_distribution": dict(daily_activity)
                },
                visualization_data={
                    "chart_type": "pie",
                    "labels": list(daily_activity.keys()),
                    "values": list(daily_activity.values()),
                    "title": "Activity Distribution by Day"
                },
                created_at=datetime.now(timezone.utc)
            ))
        
        return insights
    
    async def _generate_content_insights(self, user_id: str, data_items: List[Dict[str, Any]], 
                                       time_period: Dict[str, datetime]) -> List[Insight]:
        """Generate content trend insights"""
        insights = []
        
        # Analyze content types
        content_types = Counter()
        content_sources = Counter()
        content_sizes = []
        
        for item in data_items:
            data_type = item.get('data_type', 'unknown')
            source = item.get('source', 'unknown')
            size = item.get('size_bytes', 0)
            
            content_types[data_type] += 1
            content_sources[source] += 1
            content_sizes.append(size)
        
        # Most common content type
        if content_types:
            top_content_type = content_types.most_common(1)[0]
            
            insights.append(Insight(
                insight_id=f"content_type_trend_{user_id}",
                user_id=user_id,
                insight_type=InsightType.CONTENT_TREND,
                title="Primary Content Type",
                description=f"Your data is primarily {top_content_type[0]} ({top_content_type[1]} items, {top_content_type[1]/len(data_items)*100:.1f}%)",
                confidence=0.9,
                priority=InsightPriority.MEDIUM,
                data={
                    "primary_type": top_content_type[0],
                    "count": top_content_type[1],
                    "percentage": top_content_type[1]/len(data_items)*100,
                    "distribution": dict(content_types)
                },
                visualization_data={
                    "chart_type": "donut",
                    "labels": list(content_types.keys()),
                    "values": list(content_types.values()),
                    "title": "Content Type Distribution"
                },
                action_suggestions=[
                    f"Consider organizing your {top_content_type[0]} files",
                    "Review storage needs for your primary content type"
                ],
                created_at=datetime.now(timezone.utc)
            ))
        
        # Data source analysis
        if content_sources:
            top_source = content_sources.most_common(1)[0]
            
            insights.append(Insight(
                insight_id=f"content_source_trend_{user_id}",
                user_id=user_id,
                insight_type=InsightType.CONTENT_TREND,
                title="Primary Data Source",
                description=f"Most of your data comes from {top_source[0]} ({top_source[1]} items)",
                confidence=0.85,
                priority=InsightPriority.LOW,
                data={
                    "primary_source": top_source[0],
                    "count": top_source[1],
                    "distribution": dict(content_sources)
                },
                created_at=datetime.now(timezone.utc)
            ))
        
        return insights
    
    async def _generate_productivity_insights(self, user_id: str, data_items: List[Dict[str, Any]], 
                                            time_period: Dict[str, datetime]) -> List[Insight]:
        """Generate productivity-related insights"""
        insights = []
        
        # Analyze document creation patterns
        document_items = [item for item in data_items if item.get('data_type') == 'document']
        text_items = [item for item in data_items if item.get('data_type') == 'text']
        
        productivity_items = document_items + text_items
        
        if productivity_items:
            # Weekly productivity analysis
            weekly_productivity = defaultdict(int)
            
            for item in productivity_items:
                created_at = item.get('created_at')
                if created_at:
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    
                    week = created_at.strftime('%Y-W%U')
                    weekly_productivity[week] += 1
            
            # Calculate productivity trend
            if len(weekly_productivity) >= 2:
                weeks = sorted(weekly_productivity.keys())
                values = [weekly_productivity[week] for week in weeks]
                
                # Simple trend calculation
                if len(values) >= 2:
                    trend = "increasing" if values[-1] > values[0] else "decreasing"
                    
                    insights.append(Insight(
                        insight_id=f"productivity_trend_{user_id}",
                        user_id=user_id,
                        insight_type=InsightType.PRODUCTIVITY,
                        title=f"Productivity Trend: {trend.title()}",
                        description=f"Your document creation is {trend} over the past {len(weeks)} weeks",
                        confidence=0.75,
                        priority=InsightPriority.MEDIUM,
                        data={
                            "trend": trend,
                            "weekly_counts": dict(weekly_productivity),
                            "total_documents": len(productivity_items)
                        },
                        visualization_data={
                            "chart_type": "line",
                            "x_axis": weeks,
                            "y_axis": values,
                            "title": "Document Creation Trend"
                        },
                        action_suggestions=[
                            "Maintain consistent document creation habits" if trend == "increasing" else "Consider setting writing goals",
                            "Review your most productive periods"
                        ],
                        created_at=datetime.now(timezone.utc)
                    ))
        
        return insights
    
    async def _generate_time_insights(self, user_id: str, data_items: List[Dict[str, Any]], 
                                    time_period: Dict[str, datetime]) -> List[Insight]:
        """Generate time management insights"""
        insights = []
        
        # Analyze activity distribution across time periods
        morning_count = 0
        afternoon_count = 0
        evening_count = 0
        night_count = 0
        
        for item in data_items:
            created_at = item.get('created_at')
            if created_at:
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                hour = created_at.hour
                if 5 <= hour < 12:
                    morning_count += 1
                elif 12 <= hour < 17:
                    afternoon_count += 1
                elif 17 <= hour < 22:
                    evening_count += 1
                else:
                    night_count += 1
        
        # Determine dominant time period
        time_periods = {
            "morning": morning_count,
            "afternoon": afternoon_count,
            "evening": evening_count,
            "night": night_count
        }
        
        if any(time_periods.values()):
            dominant_period = max(time_periods.items(), key=lambda x: x[1])
            
            insights.append(Insight(
                insight_id=f"time_preference_{user_id}",
                user_id=user_id,
                insight_type=InsightType.TIME_MANAGEMENT,
                title=f"You're a {dominant_period[0].title()} Person",
                description=f"Most of your activity ({dominant_period[1]} items) happens in the {dominant_period[0]}",
                confidence=0.8,
                priority=InsightPriority.MEDIUM,
                data={
                    "dominant_period": dominant_period[0],
                    "activity_count": dominant_period[1],
                    "distribution": time_periods
                },
                visualization_data={
                    "chart_type": "radar",
                    "labels": list(time_periods.keys()),
                    "values": list(time_periods.values()),
                    "title": "Activity by Time of Day"
                },
                action_suggestions=[
                    f"Schedule important tasks during your peak {dominant_period[0]} hours",
                    "Align your work schedule with your natural rhythms"
                ],
                created_at=datetime.now(timezone.utc)
            ))
        
        return insights
    
    async def _generate_location_insights(self, user_id: str, data_items: List[Dict[str, Any]], 
                                        time_period: Dict[str, datetime]) -> List[Insight]:
        """Generate location-based insights"""
        insights = []
        
        # Analyze geospatial data items
        location_items = [item for item in data_items if item.get('data_type') == 'geospatial']
        
        if location_items:
            # Extract location patterns (mock implementation)
            locations = Counter()
            
            for item in location_items:
                # Extract location from metadata or content
                location = item.get('metadata', {}).get('location', 'unknown')
                if location != 'unknown':
                    locations[location] += 1
            
            if locations:
                top_location = locations.most_common(1)[0]
                
                insights.append(Insight(
                    insight_id=f"location_pattern_{user_id}",
                    user_id=user_id,
                    insight_type=InsightType.LOCATION_PATTERN,
                    title="Frequent Location",
                    description=f"You spend most time at {top_location[0]} ({top_location[1]} visits)",
                    confidence=0.7,
                    priority=InsightPriority.LOW,
                    data={
                        "top_location": top_location[0],
                        "visit_count": top_location[1],
                        "location_distribution": dict(locations)
                    },
                    created_at=datetime.now(timezone.utc)
                ))
        
        return insights
    
    async def _generate_storage_insights(self, user_id: str, data_items: List[Dict[str, Any]], 
                                       time_period: Dict[str, datetime]) -> List[Insight]:
        """Generate storage optimization insights"""
        insights = []
        
        # Calculate storage statistics
        total_size = sum(item.get('size_bytes', 0) for item in data_items)
        
        if total_size > 0:
            # Analyze size by type
            size_by_type = defaultdict(int)
            count_by_type = defaultdict(int)
            
            for item in data_items:
                data_type = item.get('data_type', 'unknown')
                size = item.get('size_bytes', 0)
                
                size_by_type[data_type] += size
                count_by_type[data_type] += 1
            
            # Find largest content type
            largest_type = max(size_by_type.items(), key=lambda x: x[1])
            
            # Convert to MB for readability
            total_size_mb = total_size / (1024 * 1024)
            largest_size_mb = largest_type[1] / (1024 * 1024)
            
            insights.append(Insight(
                insight_id=f"storage_usage_{user_id}",
                user_id=user_id,
                insight_type=InsightType.STORAGE_OPTIMIZATION,
                title="Storage Usage Analysis",
                description=f"Your data uses {total_size_mb:.1f} MB, with {largest_type[0]} files taking {largest_size_mb:.1f} MB ({largest_size_mb/total_size_mb*100:.1f}%)",
                confidence=0.95,
                priority=InsightPriority.HIGH if total_size_mb > 1000 else InsightPriority.MEDIUM,
                data={
                    "total_size_mb": total_size_mb,
                    "largest_type": largest_type[0],
                    "largest_size_mb": largest_size_mb,
                    "size_distribution": {k: v/(1024*1024) for k, v in size_by_type.items()}
                },
                visualization_data={
                    "chart_type": "treemap",
                    "labels": list(size_by_type.keys()),
                    "values": list(size_by_type.values()),
                    "title": "Storage Usage by Content Type"
                },
                action_suggestions=[
                    f"Review and organize your {largest_type[0]} files",
                    "Consider archiving old files to save space" if total_size_mb > 1000 else "Monitor storage growth"
                ],
                created_at=datetime.now(timezone.utc)
            ))
        
        return insights
    
    async def _generate_quality_insights(self, user_id: str, data_items: List[Dict[str, Any]], 
                                       time_period: Dict[str, datetime]) -> List[Insight]:
        """Generate content quality insights"""
        insights = []
        
        # Analyze confidence scores
        confidence_scores = [item.get('confidence_score', 0) for item in data_items if item.get('confidence_score')]
        
        if confidence_scores:
            avg_confidence = statistics.mean(confidence_scores)
            low_confidence_items = len([score for score in confidence_scores if score < 0.5])
            
            insights.append(Insight(
                insight_id=f"content_quality_{user_id}",
                user_id=user_id,
                insight_type=InsightType.CONTENT_QUALITY,
                title="Content Quality Assessment",
                description=f"Average classification confidence: {avg_confidence:.2f}. {low_confidence_items} items have low confidence.",
                confidence=0.8,
                priority=InsightPriority.HIGH if low_confidence_items > len(data_items) * 0.2 else InsightPriority.LOW,
                data={
                    "avg_confidence": avg_confidence,
                    "low_confidence_count": low_confidence_items,
                    "total_items": len(confidence_scores)
                },
                action_suggestions=[
                    "Review items with low confidence scores",
                    "Consider adding more metadata to improve classification" if low_confidence_items > 0 else "Great job maintaining high-quality data"
                ],
                created_at=datetime.now(timezone.utc)
            ))
        
        return insights
    
    async def _generate_summary_statistics(self, data_items: List[Dict[str, Any]], 
                                         time_period: Dict[str, datetime]) -> Dict[str, Any]:
        """Generate summary statistics for the data"""
        total_items = len(data_items)
        
        # Content type distribution
        content_types = Counter(item.get('data_type', 'unknown') for item in data_items)
        
        # Source distribution
        sources = Counter(item.get('source', 'unknown') for item in data_items)
        
        # Size statistics
        sizes = [item.get('size_bytes', 0) for item in data_items if item.get('size_bytes')]
        total_size = sum(sizes)
        avg_size = statistics.mean(sizes) if sizes else 0
        
        # Time distribution
        creation_times = []
        for item in data_items:
            created_at = item.get('created_at')
            if created_at:
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                creation_times.append(created_at)
        
        # Daily activity
        daily_activity = Counter()
        for dt in creation_times:
            day = dt.date()
            daily_activity[day] += 1
        
        return {
            "total_items": total_items,
            "content_types": dict(content_types),
            "sources": dict(sources),
            "storage": {
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024),
                "average_size_bytes": avg_size
            },
            "time_analysis": {
                "items_per_day": len(daily_activity),
                "avg_daily_activity": statistics.mean(daily_activity.values()) if daily_activity else 0,
                "most_active_day": max(daily_activity.items(), key=lambda x: x[1]) if daily_activity else None
            },
            "quality_metrics": {
                "classified_items": len([item for item in data_items if item.get('data_type') != 'unknown']),
                "classification_rate": len([item for item in data_items if item.get('data_type') != 'unknown']) / total_items if total_items > 0 else 0
            }
        }
    
    async def _generate_trends(self, data_items: List[Dict[str, Any]], 
                             time_period: Dict[str, datetime]) -> Dict[str, Any]:
        """Generate trend analysis"""
        trends = {}
        
        # Activity trend over time
        daily_counts = defaultdict(int)
        
        for item in data_items:
            created_at = item.get('created_at')
            if created_at:
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                day = created_at.date()
                daily_counts[day] += 1
        
        if len(daily_counts) >= 7:  # Need at least a week of data
            days = sorted(daily_counts.keys())
            counts = [daily_counts[day] for day in days]
            
            # Simple trend calculation (first half vs second half)
            mid_point = len(counts) // 2
            first_half_avg = statistics.mean(counts[:mid_point]) if mid_point > 0 else 0
            second_half_avg = statistics.mean(counts[mid_point:]) if mid_point < len(counts) else 0
            
            if second_half_avg > first_half_avg * 1.1:
                activity_trend = "increasing"
            elif second_half_avg < first_half_avg * 0.9:
                activity_trend = "decreasing"
            else:
                activity_trend = "stable"
            
            trends["activity"] = {
                "trend": activity_trend,
                "first_half_avg": first_half_avg,
                "second_half_avg": second_half_avg,
                "change_percent": ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0
            }
        
        # Content type trends
        weekly_content_types = defaultdict(lambda: defaultdict(int))
        
        for item in data_items:
            created_at = item.get('created_at')
            if created_at:
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                week = created_at.strftime('%Y-W%U')
                content_type = item.get('data_type', 'unknown')
                weekly_content_types[week][content_type] += 1
        
        trends["content_types"] = dict(weekly_content_types)
        
        return trends
    
    async def _generate_recommendations(self, insights: List[Insight], 
                                      summary_stats: Dict[str, Any], 
                                      trends: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on insights"""
        recommendations = []
        
        # High priority insights drive recommendations
        high_priority_insights = [insight for insight in insights if insight.priority == InsightPriority.HIGH]
        
        for insight in high_priority_insights:
            if insight.action_suggestions:
                recommendations.extend(insight.action_suggestions)
        
        # Storage-based recommendations
        total_size_mb = summary_stats.get("storage", {}).get("total_size_mb", 0)
        if total_size_mb > 1000:  # > 1GB
            recommendations.append("Consider archiving old files to optimize storage")
        
        # Activity-based recommendations
        if trends.get("activity", {}).get("trend") == "decreasing":
            recommendations.append("Your activity has been decreasing. Consider setting regular data organization goals")
        
        # Quality-based recommendations
        classification_rate = summary_stats.get("quality_metrics", {}).get("classification_rate", 0)
        if classification_rate < 0.8:
            recommendations.append("Improve data classification by adding more descriptive filenames and metadata")
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(recommendations))

class InsightsEngine:
    """Main insights engine that orchestrates analytics and reporting"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url
        self.analytics = DataAnalytics()
        self.cached_insights = {}
        self.cache_duration = timedelta(hours=6)  # Cache insights for 6 hours
    
    async def generate_insights(self, user_id: str, insight_types: List[InsightType] = None, 
                              force_refresh: bool = False) -> List[Insight]:
        """Generate insights for a user"""
        cache_key = f"{user_id}_{','.join([t.value for t in insight_types or []])}"
        
        # Check cache
        if not force_refresh and cache_key in self.cached_insights:
            cached_data = self.cached_insights[cache_key]
            if datetime.now(timezone.utc) - cached_data['timestamp'] < self.cache_duration:
                return cached_data['insights']
        
        # Mock user data - in production, this would query the database
        mock_data = await self._get_user_data(user_id)
        
        # Generate analytics report
        report = await self.analytics.analyze_user_data(user_id, mock_data)
        
        # Filter insights by type if specified
        insights = report.insights
        if insight_types:
            insights = [insight for insight in insights if insight.insight_type in insight_types]
        
        # Cache results
        self.cached_insights[cache_key] = {
            'timestamp': datetime.now(timezone.utc),
            'insights': insights
        }
        
        return insights
    
    async def generate_report(self, user_id: str, report_type: str = "comprehensive", 
                            time_period: Dict[str, datetime] = None) -> AnalyticsReport:
        """Generate a comprehensive analytics report"""
        mock_data = await self._get_user_data(user_id)
        report = await self.analytics.analyze_user_data(user_id, mock_data, time_period)
        return report
    
    async def get_insight_by_id(self, insight_id: str) -> Optional[Insight]:
        """Retrieve a specific insight by ID"""
        # Search through cached insights
        for cached_data in self.cached_insights.values():
            for insight in cached_data['insights']:
                if insight.insight_id == insight_id:
                    return insight
        return None
    
    async def _get_user_data(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user data for analysis (mock implementation)"""
        # In production, this would query the actual database
        # For now, return mock data
        return [
            {
                "id": f"item_{i}",
                "user_id": user_id,
                "data_type": ["image", "text", "document", "video", "audio"][i % 5],
                "source": ["google_photos", "dropbox", "email", "manual"][i % 4],
                "created_at": (datetime.now(timezone.utc) - timedelta(days=i % 30)).isoformat(),
                "size_bytes": 1024 * 1024 * (i % 10 + 1),  # 1-10 MB
                "confidence_score": 0.3 + (i % 7) * 0.1,  # 0.3-0.9
                "metadata": {
                    "location": ["home", "office", "cafe"][i % 3] if i % 2 == 0 else None
                }
            }
            for i in range(100)  # 100 mock items
        ]

# CLI Interface
async def main():
    """Command-line interface for insights engine"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ActiveLog Insights Engine')
    parser.add_argument('action', choices=['insights', 'report', 'test'])
    parser.add_argument('--user-id', default='test_user', help='User ID for analysis')
    parser.add_argument('--insight-types', nargs='+', help='Specific insight types to generate')
    parser.add_argument('--output', help='Output file for results')
    parser.add_argument('--format', choices=['json', 'summary'], default='summary', help='Output format')
    
    args = parser.parse_args()
    
    engine = InsightsEngine()
    
    if args.action == 'insights':
        # Parse insight types
        insight_types = None
        if args.insight_types:
            insight_types = []
            for type_str in args.insight_types:
                try:
                    insight_types.append(InsightType(type_str))
                except ValueError:
                    print(f"Warning: Unknown insight type '{type_str}'")
        
        # Generate insights
        insights = await engine.generate_insights(args.user_id, insight_types)
        
        if args.format == 'json':
            output = json.dumps([asdict(insight) for insight in insights], indent=2, default=str)
        else:
            output = f"Generated {len(insights)} insights for user {args.user_id}:\n\n"
            for insight in insights:
                output += f"• {insight.title}\n"
                output += f"  {insight.description}\n"
                output += f"  Priority: {insight.priority.name}, Confidence: {insight.confidence:.2f}\n\n"
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Insights saved to {args.output}")
        else:
            print(output)
    
    elif args.action == 'report':
        # Generate comprehensive report
        report = await engine.generate_report(args.user_id)
        
        if args.format == 'json':
            output = json.dumps(asdict(report), indent=2, default=str)
        else:
            output = f"Analytics Report for {args.user_id}\n"
            output += "=" * 50 + "\n\n"
            output += f"Report ID: {report.report_id}\n"
            output += f"Generated: {report.generated_at}\n"
            output += f"Time Period: {report.time_period['start']} to {report.time_period['end']}\n\n"
            
            output += "Summary Statistics:\n"
            for key, value in report.summary_statistics.items():
                if isinstance(value, dict):
                    output += f"  {key}:\n"
                    for subkey, subvalue in value.items():
                        output += f"    {subkey}: {subvalue}\n"
                else:
                    output += f"  {key}: {value}\n"
            
            output += f"\nInsights ({len(report.insights)}):\n"
            for insight in report.insights:
                output += f"  • {insight.title} [{insight.priority.name}]\n"
            
            output += f"\nRecommendations ({len(report.recommendations)}):\n"
            for rec in report.recommendations:
                output += f"  • {rec}\n"
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Report saved to {args.output}")
        else:
            print(output)
    
    elif args.action == 'test':
        # Test the insights engine with sample data
        print("Testing Insights Engine...")
        print("=" * 30)
        
        # Test different insight types
        test_types = [
            InsightType.USAGE_PATTERN,
            InsightType.CONTENT_TREND,
            InsightType.STORAGE_OPTIMIZATION
        ]
        
        for insight_type in test_types:
            print(f"\nTesting {insight_type.value}:")
            insights = await engine.generate_insights(args.user_id, [insight_type])
            
            for insight in insights:
                print(f"  ✓ {insight.title}")
                print(f"    Confidence: {insight.confidence:.2f}")
                print(f"    Priority: {insight.priority.name}")

if __name__ == "__main__":
    asyncio.run(main())