"""
Progress Visualization System for Interactive Tutorials

This module provides comprehensive progress tracking and visualization capabilities,
including charts, heat maps, learning analytics, and achievement displays.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import json
import sqlite3
from pathlib import Path
import math


class ProgressMetric(Enum):
    """Types of progress metrics to track"""
    COMPLETION_RATE = "completion_rate"
    TIME_SPENT = "time_spent"
    ACCURACY_SCORE = "accuracy_score"
    STREAK_COUNT = "streak_count"
    SKILL_LEVEL = "skill_level"
    ENGAGEMENT_SCORE = "engagement_score"
    DIFFICULTY_MASTERY = "difficulty_mastery"
    LEARNING_VELOCITY = "learning_velocity"


class ChartType(Enum):
    """Types of progress charts available"""
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    RADAR_CHART = "radar_chart"
    HEAT_MAP = "heat_map"
    PIE_CHART = "pie_chart"
    SCATTER_PLOT = "scatter_plot"
    PROGRESS_BAR = "progress_bar"
    TIMELINE = "timeline"


class TimeRange(Enum):
    """Time ranges for progress analysis"""
    LAST_HOUR = "last_hour"
    LAST_DAY = "last_day"
    LAST_WEEK = "last_week"
    LAST_MONTH = "last_month"
    LAST_QUARTER = "last_quarter"
    LAST_YEAR = "last_year"
    ALL_TIME = "all_time"


@dataclass
class ProgressDataPoint:
    """Individual progress measurement"""
    timestamp: datetime
    metric: ProgressMetric
    value: float
    context: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    module_id: Optional[str] = None


@dataclass
class ChartConfiguration:
    """Configuration for chart rendering"""
    chart_type: ChartType
    title: str
    metrics: List[ProgressMetric]
    time_range: TimeRange
    width: int = 800
    height: int = 400
    color_scheme: str = "default"
    show_grid: bool = True
    show_labels: bool = True
    interactive: bool = True
    animation_duration: float = 1.0


@dataclass
class LearningAnalytics:
    """Advanced learning analytics data"""
    total_sessions: int
    total_time_minutes: float
    average_session_duration: float
    completion_percentage: float
    accuracy_trend: List[float]
    learning_velocity: float
    skill_distribution: Dict[str, float]
    engagement_patterns: Dict[str, float]
    peak_learning_hours: List[int]
    struggle_areas: List[str]
    strength_areas: List[str]


@dataclass
class ProgressVisualization:
    """Complete progress visualization"""
    chart_data: Dict[str, Any]
    analytics: LearningAnalytics
    recommendations: List[str]
    milestones: List[Dict[str, Any]]
    generated_at: datetime = field(default_factory=datetime.now)


class ProgressTracker:
    """Tracks and stores progress data"""
    
    def __init__(self, db_path: str = "progress_data.db"):
        self.db_path = Path(db_path)
        self.init_database()
    
    def init_database(self):
        """Initialize progress tracking database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS progress_data (
                    id INTEGER PRIMARY KEY,
                    user_id TEXT,
                    timestamp DATETIME,
                    metric TEXT,
                    value REAL,
                    context TEXT,
                    session_id TEXT,
                    module_id TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learning_sessions (
                    id INTEGER PRIMARY KEY,
                    user_id TEXT,
                    session_id TEXT,
                    start_time DATETIME,
                    end_time DATETIME,
                    module_id TEXT,
                    completed BOOLEAN,
                    final_score REAL
                )
            """)
    
    def record_progress(self, user_id: str, data_point: ProgressDataPoint):
        """Record a progress data point"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO progress_data 
                (user_id, timestamp, metric, value, context, session_id, module_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                data_point.timestamp.isoformat(),
                data_point.metric.value,
                data_point.value,
                json.dumps(data_point.context),
                data_point.session_id,
                data_point.module_id
            ))
    
    def get_progress_data(self, user_id: str, time_range: TimeRange, 
                         metrics: List[ProgressMetric]) -> List[ProgressDataPoint]:
        """Retrieve progress data for specified time range and metrics"""
        start_time = self._get_time_range_start(time_range)
        metric_names = [m.value for m in metrics]
        placeholders = ','.join(['?' for _ in metric_names])
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"""
                SELECT timestamp, metric, value, context, session_id, module_id
                FROM progress_data
                WHERE user_id = ? AND timestamp >= ? AND metric IN ({placeholders})
                ORDER BY timestamp
            """, [user_id, start_time.isoformat()] + metric_names)
            
            return [
                ProgressDataPoint(
                    timestamp=datetime.fromisoformat(row[0]),
                    metric=ProgressMetric(row[1]),
                    value=row[2],
                    context=json.loads(row[3]) if row[3] else {},
                    session_id=row[4],
                    module_id=row[5]
                )
                for row in cursor.fetchall()
            ]
    
    def _get_time_range_start(self, time_range: TimeRange) -> datetime:
        """Get start datetime for time range"""
        now = datetime.now()
        if time_range == TimeRange.LAST_HOUR:
            return now - timedelta(hours=1)
        elif time_range == TimeRange.LAST_DAY:
            return now - timedelta(days=1)
        elif time_range == TimeRange.LAST_WEEK:
            return now - timedelta(weeks=1)
        elif time_range == TimeRange.LAST_MONTH:
            return now - timedelta(days=30)
        elif time_range == TimeRange.LAST_QUARTER:
            return now - timedelta(days=90)
        elif time_range == TimeRange.LAST_YEAR:
            return now - timedelta(days=365)
        else:
            return datetime(2020, 1, 1)  # All time


class ChartRenderer:
    """Renders progress charts in various formats"""
    
    def render_line_chart(self, data: List[ProgressDataPoint], config: ChartConfiguration) -> Dict[str, Any]:
        """Render line chart data"""
        # Group data by metric
        chart_data = {}
        for metric in config.metrics:
            metric_data = [d for d in data if d.metric == metric]
            chart_data[metric.value] = {
                'x': [d.timestamp.isoformat() for d in metric_data],
                'y': [d.value for d in metric_data],
                'type': 'line',
                'name': metric.value.replace('_', ' ').title()
            }
        
        return {
            'data': list(chart_data.values()),
            'layout': {
                'title': config.title,
                'xaxis': {'title': 'Time'},
                'yaxis': {'title': 'Value'},
                'width': config.width,
                'height': config.height,
                'showlegend': True
            }
        }
    
    def render_radar_chart(self, data: List[ProgressDataPoint], config: ChartConfiguration) -> Dict[str, Any]:
        """Render radar chart showing skill levels"""
        # Calculate average values for each metric
        metric_averages = {}
        for metric in config.metrics:
            metric_data = [d.value for d in data if d.metric == metric]
            metric_averages[metric.value] = sum(metric_data) / len(metric_data) if metric_data else 0
        
        return {
            'data': [{
                'type': 'radar',
                'r': list(metric_averages.values()),
                'theta': [m.replace('_', ' ').title() for m in metric_averages.keys()],
                'fill': 'toself',
                'name': 'Current Skills'
            }],
            'layout': {
                'title': config.title,
                'polar': {
                    'radialaxis': {
                        'visible': True,
                        'range': [0, 100]
                    }
                }
            }
        }
    
    def render_heat_map(self, data: List[ProgressDataPoint], config: ChartConfiguration) -> Dict[str, Any]:
        """Render heat map showing activity patterns"""
        # Create 24x7 grid (hours x days of week)
        heat_data = [[0 for _ in range(7)] for _ in range(24)]
        
        for point in data:
            hour = point.timestamp.hour
            day = point.timestamp.weekday()
            heat_data[hour][day] += point.value
        
        return {
            'data': [{
                'z': heat_data,
                'type': 'heatmap',
                'colorscale': 'Blues',
                'x': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                'y': [f'{i:02d}:00' for i in range(24)]
            }],
            'layout': {
                'title': config.title,
                'xaxis': {'title': 'Day of Week'},
                'yaxis': {'title': 'Hour of Day'}
            }
        }


class AnalyticsEngine:
    """Generates advanced learning analytics"""
    
    def __init__(self, progress_tracker: ProgressTracker):
        self.tracker = progress_tracker
    
    def generate_analytics(self, user_id: str, time_range: TimeRange) -> LearningAnalytics:
        """Generate comprehensive learning analytics"""
        # Get all progress data for the time range
        all_metrics = list(ProgressMetric)
        data = self.tracker.get_progress_data(user_id, time_range, all_metrics)
        
        # Calculate session statistics
        sessions = self._get_unique_sessions(data)
        total_sessions = len(sessions)
        
        # Calculate time statistics
        total_time = self._calculate_total_time(data)
        avg_session_duration = total_time / total_sessions if total_sessions > 0 else 0
        
        # Calculate completion percentage
        completion_data = [d.value for d in data if d.metric == ProgressMetric.COMPLETION_RATE]
        completion_percentage = sum(completion_data) / len(completion_data) if completion_data else 0
        
        # Calculate accuracy trend
        accuracy_data = [d.value for d in data if d.metric == ProgressMetric.ACCURACY_SCORE]
        accuracy_trend = self._calculate_trend(accuracy_data)
        
        # Calculate learning velocity
        learning_velocity = self._calculate_learning_velocity(data)
        
        # Analyze skill distribution
        skill_distribution = self._analyze_skill_distribution(data)
        
        # Analyze engagement patterns
        engagement_patterns = self._analyze_engagement_patterns(data)
        
        # Find peak learning hours
        peak_learning_hours = self._find_peak_learning_hours(data)
        
        # Identify struggle and strength areas
        struggle_areas, strength_areas = self._identify_performance_areas(data)
        
        return LearningAnalytics(
            total_sessions=total_sessions,
            total_time_minutes=total_time,
            average_session_duration=avg_session_duration,
            completion_percentage=completion_percentage,
            accuracy_trend=accuracy_trend,
            learning_velocity=learning_velocity,
            skill_distribution=skill_distribution,
            engagement_patterns=engagement_patterns,
            peak_learning_hours=peak_learning_hours,
            struggle_areas=struggle_areas,
            strength_areas=strength_areas
        )
    
    def _get_unique_sessions(self, data: List[ProgressDataPoint]) -> List[str]:
        """Get unique session IDs from data"""
        return list(set(d.session_id for d in data if d.session_id))
    
    def _calculate_total_time(self, data: List[ProgressDataPoint]) -> float:
        """Calculate total learning time in minutes"""
        time_data = [d.value for d in data if d.metric == ProgressMetric.TIME_SPENT]
        return sum(time_data)
    
    def _calculate_trend(self, values: List[float]) -> List[float]:
        """Calculate trend line for values"""
        if len(values) < 2:
            return values
        
        # Simple moving average for trend
        window_size = min(5, len(values))
        trend = []
        for i in range(len(values)):
            start = max(0, i - window_size + 1)
            window = values[start:i+1]
            trend.append(sum(window) / len(window))
        return trend
    
    def _calculate_learning_velocity(self, data: List[ProgressDataPoint]) -> float:
        """Calculate learning velocity (improvement rate)"""
        skill_data = [d for d in data if d.metric == ProgressMetric.SKILL_LEVEL]
        if len(skill_data) < 2:
            return 0.0
        
        # Calculate average improvement per session
        first_skill = skill_data[0].value
        last_skill = skill_data[-1].value
        time_diff_hours = (skill_data[-1].timestamp - skill_data[0].timestamp).total_seconds() / 3600
        
        return (last_skill - first_skill) / time_diff_hours if time_diff_hours > 0 else 0.0
    
    def _analyze_skill_distribution(self, data: List[ProgressDataPoint]) -> Dict[str, float]:
        """Analyze distribution of skills across modules"""
        skill_data = [d for d in data if d.metric == ProgressMetric.SKILL_LEVEL and d.module_id]
        
        module_skills = {}
        for point in skill_data:
            if point.module_id not in module_skills:
                module_skills[point.module_id] = []
            module_skills[point.module_id].append(point.value)
        
        return {module: sum(values) / len(values) for module, values in module_skills.items()}
    
    def _analyze_engagement_patterns(self, data: List[ProgressDataPoint]) -> Dict[str, float]:
        """Analyze user engagement patterns"""
        engagement_data = [d for d in data if d.metric == ProgressMetric.ENGAGEMENT_SCORE]
        
        # Analyze by time of day
        hourly_engagement = {}
        for point in engagement_data:
            hour = point.timestamp.hour
            if hour not in hourly_engagement:
                hourly_engagement[hour] = []
            hourly_engagement[hour].append(point.value)
        
        return {f"hour_{hour}": sum(values) / len(values) 
                for hour, values in hourly_engagement.items()}
    
    def _find_peak_learning_hours(self, data: List[ProgressDataPoint]) -> List[int]:
        """Find hours with highest learning activity"""
        hourly_activity = {}
        for point in data:
            hour = point.timestamp.hour
            hourly_activity[hour] = hourly_activity.get(hour, 0) + 1
        
        # Return top 3 hours
        sorted_hours = sorted(hourly_activity.items(), key=lambda x: x[1], reverse=True)
        return [hour for hour, _ in sorted_hours[:3]]
    
    def _identify_performance_areas(self, data: List[ProgressDataPoint]) -> Tuple[List[str], List[str]]:
        """Identify areas of struggle and strength"""
        accuracy_by_module = {}
        for point in data:
            if point.metric == ProgressMetric.ACCURACY_SCORE and point.module_id:
                if point.module_id not in accuracy_by_module:
                    accuracy_by_module[point.module_id] = []
                accuracy_by_module[point.module_id].append(point.value)
        
        module_averages = {module: sum(values) / len(values) 
                          for module, values in accuracy_by_module.items()}
        
        # Areas with accuracy < 60% are struggles, > 85% are strengths
        struggle_areas = [module for module, avg in module_averages.items() if avg < 60]
        strength_areas = [module for module, avg in module_averages.items() if avg > 85]
        
        return struggle_areas, strength_areas


class ProgressVisualizer:
    """Main progress visualization system"""
    
    def __init__(self, db_path: str = "progress_data.db"):
        self.tracker = ProgressTracker(db_path)
        self.renderer = ChartRenderer()
        self.analytics = AnalyticsEngine(self.tracker)
    
    def create_visualization(self, user_id: str, config: ChartConfiguration) -> ProgressVisualization:
        """Create complete progress visualization"""
        # Get progress data
        data = self.tracker.get_progress_data(user_id, config.time_range, config.metrics)
        
        # Generate chart
        if config.chart_type == ChartType.LINE_CHART:
            chart_data = self.renderer.render_line_chart(data, config)
        elif config.chart_type == ChartType.RADAR_CHART:
            chart_data = self.renderer.render_radar_chart(data, config)
        elif config.chart_type == ChartType.HEAT_MAP:
            chart_data = self.renderer.render_heat_map(data, config)
        else:
            chart_data = self.renderer.render_line_chart(data, config)  # Default
        
        # Generate analytics
        analytics = self.analytics.generate_analytics(user_id, config.time_range)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(analytics)
        
        # Generate milestones
        milestones = self._generate_milestones(data, analytics)
        
        return ProgressVisualization(
            chart_data=chart_data,
            analytics=analytics,
            recommendations=recommendations,
            milestones=milestones
        )
    
    def get_dashboard_data(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        # Create multiple visualizations for dashboard
        visualizations = {}
        
        # Skills radar chart
        skills_config = ChartConfiguration(
            chart_type=ChartType.RADAR_CHART,
            title="Skill Levels",
            metrics=[ProgressMetric.SKILL_LEVEL],
            time_range=TimeRange.LAST_MONTH
        )
        visualizations['skills'] = self.create_visualization(user_id, skills_config)
        
        # Progress over time
        progress_config = ChartConfiguration(
            chart_type=ChartType.LINE_CHART,
            title="Progress Over Time",
            metrics=[ProgressMetric.COMPLETION_RATE, ProgressMetric.ACCURACY_SCORE],
            time_range=TimeRange.LAST_WEEK
        )
        visualizations['progress'] = self.create_visualization(user_id, progress_config)
        
        # Activity heat map
        activity_config = ChartConfiguration(
            chart_type=ChartType.HEAT_MAP,
            title="Learning Activity Pattern",
            metrics=[ProgressMetric.ENGAGEMENT_SCORE],
            time_range=TimeRange.LAST_MONTH
        )
        visualizations['activity'] = self.create_visualization(user_id, activity_config)
        
        return {
            'user_id': user_id,
            'generated_at': datetime.now().isoformat(),
            'visualizations': visualizations
        }
    
    def _generate_recommendations(self, analytics: LearningAnalytics) -> List[str]:
        """Generate personalized learning recommendations"""
        recommendations = []
        
        # Based on learning velocity
        if analytics.learning_velocity < 0.1:
            recommendations.append("Consider increasing practice frequency to improve learning velocity")
        
        # Based on accuracy trend
        if analytics.accuracy_trend and len(analytics.accuracy_trend) > 1:
            recent_accuracy = analytics.accuracy_trend[-1]
            if recent_accuracy < 70:
                recommendations.append("Focus on reviewing fundamentals to improve accuracy")
        
        # Based on engagement patterns
        if analytics.engagement_patterns:
            peak_hours = [int(k.split('_')[1]) for k in analytics.engagement_patterns.keys() 
                         if analytics.engagement_patterns[k] > 80]
            if peak_hours:
                recommendations.append(f"Schedule learning sessions during peak hours: {', '.join(map(str, peak_hours))}")
        
        # Based on struggle areas
        if analytics.struggle_areas:
            recommendations.append(f"Focus extra attention on: {', '.join(analytics.struggle_areas)}")
        
        return recommendations
    
    def _generate_milestones(self, data: List[ProgressDataPoint], analytics: LearningAnalytics) -> List[Dict[str, Any]]:
        """Generate milestone achievements"""
        milestones = []
        
        # Time-based milestones
        if analytics.total_time_minutes > 60:
            milestones.append({
                'type': 'time_milestone',
                'title': 'Hour of Learning',
                'description': f'Completed {analytics.total_time_minutes:.0f} minutes of learning',
                'icon': 'clock',
                'achieved': True
            })
        
        # Session-based milestones
        if analytics.total_sessions >= 10:
            milestones.append({
                'type': 'session_milestone',
                'title': 'Dedicated Learner',
                'description': f'Completed {analytics.total_sessions} learning sessions',
                'icon': 'trophy',
                'achieved': True
            })
        
        # Accuracy milestones
        if analytics.completion_percentage > 90:
            milestones.append({
                'type': 'accuracy_milestone',
                'title': 'Excellence',
                'description': f'Achieved {analytics.completion_percentage:.1f}% completion rate',
                'icon': 'star',
                'achieved': True
            })
        
        return milestones


# Example usage and testing
if __name__ == "__main__":
    # Initialize progress visualizer
    visualizer = ProgressVisualizer("test_progress.db")
    
    # Record some sample progress data
    user_id = "user123"
    
    # Simulate learning session data
    import random
    from datetime import datetime, timedelta
    
    base_time = datetime.now() - timedelta(days=30)
    
    for day in range(30):
        for session in range(random.randint(0, 3)):
            session_time = base_time + timedelta(days=day, hours=random.randint(8, 22))
            session_id = f"session_{day}_{session}"
            
            # Record various metrics
            visualizer.tracker.record_progress(user_id, ProgressDataPoint(
                timestamp=session_time,
                metric=ProgressMetric.COMPLETION_RATE,
                value=random.uniform(70, 100),
                session_id=session_id,
                module_id=f"module_{random.randint(1, 5)}"
            ))
            
            visualizer.tracker.record_progress(user_id, ProgressDataPoint(
                timestamp=session_time,
                metric=ProgressMetric.ACCURACY_SCORE,
                value=random.uniform(60, 95),
                session_id=session_id
            ))
            
            visualizer.tracker.record_progress(user_id, ProgressDataPoint(
                timestamp=session_time,
                metric=ProgressMetric.SKILL_LEVEL,
                value=random.uniform(1, 10),
                session_id=session_id
            ))
    
    # Generate dashboard
    dashboard = visualizer.get_dashboard_data(user_id)
    print("Dashboard generated successfully!")
    print(f"Generated {len(dashboard['visualizations'])} visualizations")