"""
Bot Performance Analytics and Visualization System
Advanced analytics engine with ML-powered insights and interactive visualizations
"""

import asyncio
import json
import logging
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import sqlite3
import threading
from collections import defaultdict, deque
import uuid
import statistics
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


class AnalyticsMetric(Enum):
    """Types of analytics metrics"""
    TASK_COMPLETION_RATE = "task_completion_rate"
    AVERAGE_EXECUTION_TIME = "average_execution_time"
    COST_EFFICIENCY = "cost_efficiency"
    ERROR_RATE = "error_rate"
    COLLABORATION_SUCCESS_RATE = "collaboration_success_rate"
    BOT_UTILIZATION = "bot_utilization"
    THROUGHPUT = "throughput"
    QUALITY_SCORE = "quality_score"
    RESOURCE_CONTENTION = "resource_contention"
    RESPONSE_TIME = "response_time"
    KNOWLEDGE_SHARING_RATE = "knowledge_sharing_rate"
    SYNC_EFFICIENCY = "sync_efficiency"


class InsightType(Enum):
    """Types of insights generated"""
    PERFORMANCE_TREND = "performance_trend"
    ANOMALY_DETECTION = "anomaly_detection"
    OPTIMIZATION_OPPORTUNITY = "optimization_opportunity"
    BOTTLENECK_IDENTIFICATION = "bottleneck_identification"
    COST_REDUCTION = "cost_reduction"
    PATTERN_RECOGNITION = "pattern_recognition"
    PREDICTION = "prediction"
    RECOMMENDATION = "recommendation"


class InsightSeverity(Enum):
    """Severity levels for insights"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DataPoint:
    """Individual data point for analytics"""
    timestamp: datetime
    metric: AnalyticsMetric
    value: float
    bot_id: Optional[str] = None
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceInsight:
    """Analytics insight with recommendations"""
    insight_id: str
    insight_type: InsightType
    severity: InsightSeverity
    title: str
    description: str
    affected_entities: List[str]  # bot_ids, task_ids, etc.
    metrics_involved: List[AnalyticsMetric]
    confidence_score: float
    supporting_data: Dict[str, Any]
    recommendations: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None


@dataclass
class BotPerformanceProfile:
    """Comprehensive bot performance profile"""
    bot_id: str
    
    # Core performance metrics
    total_tasks_completed: int = 0
    success_rate: float = 0.0
    average_execution_time: float = 0.0
    cost_efficiency: float = 0.0
    quality_score: float = 0.0
    
    # Collaboration metrics
    collaboration_count: int = 0
    collaboration_success_rate: float = 0.0
    knowledge_sharing_frequency: float = 0.0
    sync_efficiency: float = 0.0
    
    # Specialization metrics
    preferred_task_types: List[str] = field(default_factory=list)
    expertise_areas: List[str] = field(default_factory=list)
    complexity_handling: Dict[str, float] = field(default_factory=dict)
    
    # Temporal patterns
    peak_performance_hours: List[int] = field(default_factory=list)
    workload_patterns: Dict[str, float] = field(default_factory=dict)
    
    # Trends and predictions
    performance_trend: str = "stable"  # improving, declining, stable, volatile
    predicted_next_month_performance: Optional[float] = None
    efficiency_percentile: float = 0.0
    
    # Anomaly detection
    recent_anomalies: List[Dict[str, Any]] = field(default_factory=list)
    anomaly_score: float = 0.0


@dataclass
class SystemPerformanceSnapshot:
    """System-wide performance snapshot"""
    timestamp: datetime
    
    # Overall metrics
    active_bots: int
    active_tasks: int
    active_collaborations: int
    
    # Performance metrics
    system_throughput: float
    average_response_time: float
    overall_success_rate: float
    total_cost_per_hour: float
    
    # Resource utilization
    bot_utilization_rate: float
    resource_contention_level: float
    queue_length: int
    
    # Quality metrics
    average_quality_score: float
    customer_satisfaction: float
    error_rate: float


class PerformanceAnalyzer:
    """Advanced performance analytics and visualization engine"""
    
    def __init__(
        self,
        db_path: str = "/home/activeloguser/activelog/data/performance_analytics.db",
        data_retention_days: int = 90
    ):
        self.db_path = db_path
        self.data_retention_days = data_retention_days
        
        # Data storage
        self.data_points: deque = deque(maxlen=10000)
        self.bot_profiles: Dict[str, BotPerformanceProfile] = {}
        self.insights: Dict[str, PerformanceInsight] = {}
        self.system_snapshots: deque = deque(maxlen=1000)
        
        # ML models
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        self.clustering_model = KMeans(n_clusters=5, random_state=42)
        self.trend_model = LinearRegression()
        
        # Analytics state
        self.analytics_lock = threading.RLock()
        self.running = False
        self.analyzer_task = None
        self.insights_task = None
        
        # Initialize database and ML models
        self._init_database()
        self.start_analytics_engine()
    
    def _init_database(self):
        """Initialize analytics database"""
        with sqlite3.connect(self.db_path) as conn:
            # Data points table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS data_points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    value REAL NOT NULL,
                    bot_id TEXT,
                    task_id TEXT,
                    session_id TEXT,
                    metadata TEXT
                )
            """)
            
            # Bot performance profiles
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_profiles (
                    bot_id TEXT PRIMARY KEY,
                    profile_data TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Performance insights
            conn.execute("""
                CREATE TABLE IF NOT EXISTS insights (
                    insight_id TEXT PRIMARY KEY,
                    insight_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    affected_entities TEXT NOT NULL,
                    metrics_involved TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    supporting_data TEXT NOT NULL,
                    recommendations TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT
                )
            """)
            
            # System performance snapshots
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    snapshot_data TEXT NOT NULL
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_data_points_timestamp ON data_points(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_data_points_metric ON data_points(metric)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_data_points_bot_id ON data_points(bot_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_insights_created ON insights(created_at)")
    
    def start_analytics_engine(self):
        """Start background analytics tasks"""
        if not self.running:
            self.running = True
            self.analyzer_task = threading.Thread(target=self._analytics_processor, daemon=True)
            self.insights_task = threading.Thread(target=self._insights_generator, daemon=True)
            self.analyzer_task.start()
            self.insights_task.start()
    
    def stop_analytics_engine(self):
        """Stop background analytics tasks"""
        self.running = False
        if self.analyzer_task:
            self.analyzer_task.join(timeout=5)
        if self.insights_task:
            self.insights_task.join(timeout=5)
    
    def record_data_point(
        self,
        metric: AnalyticsMetric,
        value: float,
        bot_id: Optional[str] = None,
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a new data point for analytics"""
        data_point = DataPoint(
            timestamp=datetime.now(),
            metric=metric,
            value=value,
            bot_id=bot_id,
            task_id=task_id,
            session_id=session_id,
            metadata=metadata or {}
        )
        
        with self.analytics_lock:
            self.data_points.append(data_point)
        
        # Persist to database
        self._persist_data_point(data_point)
        
        # Trigger real-time analysis
        if len(self.data_points) % 10 == 0:  # Analyze every 10 points
            threading.Thread(target=self._trigger_real_time_analysis, daemon=True).start()
    
    def record_system_snapshot(self, snapshot: SystemPerformanceSnapshot):
        """Record system performance snapshot"""
        with self.analytics_lock:
            self.system_snapshots.append(snapshot)
        
        # Persist to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO system_snapshots (timestamp, snapshot_data)
                VALUES (?, ?)
            """, (
                snapshot.timestamp.isoformat(),
                json.dumps(asdict(snapshot))
            ))
    
    def get_bot_performance_profile(self, bot_id: str) -> Optional[BotPerformanceProfile]:
        """Get comprehensive performance profile for a bot"""
        if bot_id in self.bot_profiles:
            return self.bot_profiles[bot_id]
        
        # Calculate profile from data points
        profile = self._calculate_bot_profile(bot_id)
        if profile:
            self.bot_profiles[bot_id] = profile
            self._persist_bot_profile(profile)
        
        return profile
    
    def get_performance_trends(
        self,
        metric: AnalyticsMetric,
        time_window: timedelta = timedelta(days=7),
        bot_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get performance trends for a specific metric"""
        end_time = datetime.now()
        start_time = end_time - time_window
        
        # Filter data points
        filtered_points = [
            dp for dp in self.data_points
            if (dp.metric == metric and
                start_time <= dp.timestamp <= end_time and
                (bot_id is None or dp.bot_id == bot_id))
        ]
        
        if not filtered_points:
            return {"trend": "no_data", "data_points": []}
        
        # Calculate trend
        timestamps = [(dp.timestamp - start_time).total_seconds() for dp in filtered_points]
        values = [dp.value for dp in filtered_points]
        
        # Fit linear regression for trend
        if len(timestamps) > 1:
            X = np.array(timestamps).reshape(-1, 1)
            y = np.array(values)
            
            self.trend_model.fit(X, y)
            slope = self.trend_model.coef_[0]
            
            if slope > 0.01:
                trend = "improving"
            elif slope < -0.01:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        # Calculate additional statistics
        mean_value = statistics.mean(values)
        std_dev = statistics.stdev(values) if len(values) > 1 else 0
        min_value = min(values)
        max_value = max(values)
        
        return {
            "trend": trend,
            "slope": slope if len(timestamps) > 1 else 0,
            "mean": mean_value,
            "std_dev": std_dev,
            "min": min_value,
            "max": max_value,
            "data_points": len(filtered_points),
            "time_series": [
                {"timestamp": dp.timestamp.isoformat(), "value": dp.value}
                for dp in filtered_points
            ]
        }
    
    def detect_anomalies(
        self,
        metric: AnalyticsMetric,
        bot_id: Optional[str] = None,
        lookback_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Detect anomalies in performance metrics"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=lookback_hours)
        
        # Filter data points
        filtered_points = [
            dp for dp in self.data_points
            if (dp.metric == metric and
                start_time <= dp.timestamp <= end_time and
                (bot_id is None or dp.bot_id == bot_id))
        ]
        
        if len(filtered_points) < 10:  # Need minimum data for anomaly detection
            return []
        
        # Prepare data for anomaly detection
        features = []
        for dp in filtered_points:
            # Create feature vector (value, hour of day, day of week)
            hour = dp.timestamp.hour
            day_of_week = dp.timestamp.weekday()
            features.append([dp.value, hour, day_of_week])
        
        features_array = np.array(features)
        scaled_features = self.scaler.fit_transform(features_array)
        
        # Detect anomalies
        anomalies = self.anomaly_detector.fit_predict(scaled_features)
        
        # Collect anomalous points
        anomalous_points = []
        for i, is_anomaly in enumerate(anomalies):
            if is_anomaly == -1:  # -1 indicates anomaly
                dp = filtered_points[i]
                anomalous_points.append({
                    "timestamp": dp.timestamp.isoformat(),
                    "value": dp.value,
                    "bot_id": dp.bot_id,
                    "task_id": dp.task_id,
                    "session_id": dp.session_id,
                    "deviation_score": abs(dp.value - statistics.mean([p.value for p in filtered_points])),
                    "metadata": dp.metadata
                })
        
        return anomalous_points
    
    def generate_performance_visualization(
        self,
        visualization_type: str,
        metric: AnalyticsMetric,
        time_window: timedelta = timedelta(days=7),
        bot_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate interactive visualizations using Plotly"""
        end_time = datetime.now()
        start_time = end_time - time_window
        
        # Filter data points
        filtered_points = [
            dp for dp in self.data_points
            if (dp.metric == metric and
                start_time <= dp.timestamp <= end_time and
                (bot_ids is None or dp.bot_id in bot_ids))
        ]
        
        if not filtered_points:
            return {"error": "No data available for visualization"}
        
        # Create DataFrame for easier manipulation
        df_data = []
        for dp in filtered_points:
            df_data.append({
                "timestamp": dp.timestamp,
                "value": dp.value,
                "bot_id": dp.bot_id or "system",
                "task_id": dp.task_id,
                "session_id": dp.session_id
            })
        
        df = pd.DataFrame(df_data)
        
        if visualization_type == "time_series":
            return self._create_time_series_chart(df, metric)
        elif visualization_type == "box_plot":
            return self._create_box_plot(df, metric)
        elif visualization_type == "heatmap":
            return self._create_performance_heatmap(df, metric)
        elif visualization_type == "scatter":
            return self._create_scatter_plot(df, metric)
        elif visualization_type == "distribution":
            return self._create_distribution_chart(df, metric)
        elif visualization_type == "correlation":
            return self._create_correlation_matrix(df, metric)
        else:
            return {"error": f"Unknown visualization type: {visualization_type}"}
    
    def _create_time_series_chart(self, df: pd.DataFrame, metric: AnalyticsMetric) -> Dict[str, Any]:
        """Create time series visualization"""
        fig = go.Figure()
        
        # Group by bot_id for separate lines
        for bot_id in df['bot_id'].unique():
            bot_data = df[df['bot_id'] == bot_id]
            fig.add_trace(go.Scatter(
                x=bot_data['timestamp'],
                y=bot_data['value'],
                mode='lines+markers',
                name=bot_id,
                hovertemplate='<b>%{fullData.name}</b><br>' +
                              'Time: %{x}<br>' +
                              'Value: %{y:.2f}<br>' +
                              '<extra></extra>'
            ))
        
        # Add trend line
        if len(df) > 1:
            timestamps = pd.to_numeric(df['timestamp']) / 10**9  # Convert to seconds
            z = np.polyfit(timestamps, df['value'], 1)
            p = np.poly1d(z)
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=p(timestamps),
                mode='lines',
                name='Trend',
                line=dict(dash='dash', color='red'),
                hovertemplate='Trend Line<extra></extra>'
            ))
        
        fig.update_layout(
            title=f"{metric.value.replace('_', ' ').title()} Over Time",
            xaxis_title="Time",
            yaxis_title=metric.value.replace('_', ' ').title(),
            hovermode='closest'
        )
        
        return {"chart": fig.to_json(), "type": "time_series"}
    
    def _create_box_plot(self, df: pd.DataFrame, metric: AnalyticsMetric) -> Dict[str, Any]:
        """Create box plot for performance comparison"""
        fig = go.Figure()
        
        for bot_id in df['bot_id'].unique():
            bot_data = df[df['bot_id'] == bot_id]
            fig.add_trace(go.Box(
                y=bot_data['value'],
                name=bot_id,
                boxpoints='outliers'
            ))
        
        fig.update_layout(
            title=f"{metric.value.replace('_', ' ').title()} Distribution by Bot",
            yaxis_title=metric.value.replace('_', ' ').title(),
            xaxis_title="Bot ID"
        )
        
        return {"chart": fig.to_json(), "type": "box_plot"}
    
    def _create_performance_heatmap(self, df: pd.DataFrame, metric: AnalyticsMetric) -> Dict[str, Any]:
        """Create performance heatmap"""
        # Group by hour and day of week
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.day_name()
        
        # Create pivot table
        heatmap_data = df.groupby(['day_of_week', 'hour'])['value'].mean().unstack()
        
        # Reorder days
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        heatmap_data = heatmap_data.reindex(day_order)
        
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=list(range(24)),
            y=day_order,
            colorscale='RdYlBu_r',
            hoverongaps=False,
            hovertemplate='Day: %{y}<br>Hour: %{x}<br>Avg Value: %{z:.2f}<extra></extra>'
        ))
        
        fig.update_layout(
            title=f"Average {metric.value.replace('_', ' ').title()} by Day and Hour",
            xaxis_title="Hour of Day",
            yaxis_title="Day of Week"
        )
        
        return {"chart": fig.to_json(), "type": "heatmap"}
    
    def _create_scatter_plot(self, df: pd.DataFrame, metric: AnalyticsMetric) -> Dict[str, Any]:
        """Create scatter plot with correlation analysis"""
        # Create time-based features for correlation
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.weekday()
        
        fig = go.Figure()
        
        for bot_id in df['bot_id'].unique():
            bot_data = df[df['bot_id'] == bot_id]
            fig.add_trace(go.Scatter(
                x=bot_data['hour'],
                y=bot_data['value'],
                mode='markers',
                name=bot_id,
                opacity=0.7,
                hovertemplate=f'<b>{bot_id}</b><br>' +
                              'Hour: %{x}<br>' +
                              'Value: %{y:.2f}<br>' +
                              '<extra></extra>'
            ))
        
        fig.update_layout(
            title=f"{metric.value.replace('_', ' ').title()} vs Hour of Day",
            xaxis_title="Hour of Day",
            yaxis_title=metric.value.replace('_', ' ').title()
        )
        
        return {"chart": fig.to_json(), "type": "scatter"}
    
    def _create_distribution_chart(self, df: pd.DataFrame, metric: AnalyticsMetric) -> Dict[str, Any]:
        """Create distribution histogram"""
        fig = go.Figure()
        
        for bot_id in df['bot_id'].unique():
            bot_data = df[df['bot_id'] == bot_id]
            fig.add_trace(go.Histogram(
                x=bot_data['value'],
                name=bot_id,
                opacity=0.7,
                nbinsx=20
            ))
        
        fig.update_layout(
            title=f"{metric.value.replace('_', ' ').title()} Distribution",
            xaxis_title=metric.value.replace('_', ' ').title(),
            yaxis_title="Frequency",
            barmode='overlay'
        )
        
        return {"chart": fig.to_json(), "type": "distribution"}
    
    def _create_correlation_matrix(self, df: pd.DataFrame, metric: AnalyticsMetric) -> Dict[str, Any]:
        """Create correlation matrix if multiple metrics available"""
        # This would need multiple metrics - simplified version
        correlation_data = np.random.rand(5, 5)  # Mock data
        metrics = ['Execution Time', 'Cost', 'Quality', 'Success Rate', 'Efficiency']
        
        fig = go.Figure(data=go.Heatmap(
            z=correlation_data,
            x=metrics,
            y=metrics,
            colorscale='RdBu',
            zmid=0,
            hovertemplate='%{y} vs %{x}<br>Correlation: %{z:.2f}<extra></extra>'
        ))
        
        fig.update_layout(
            title="Performance Metrics Correlation Matrix",
            xaxis_title="Metrics",
            yaxis_title="Metrics"
        )
        
        return {"chart": fig.to_json(), "type": "correlation"}
    
    def get_insights(self, severity_filter: Optional[InsightSeverity] = None) -> List[PerformanceInsight]:
        """Get performance insights with optional filtering"""
        insights = list(self.insights.values())
        
        if severity_filter:
            insights = [i for i in insights if i.severity == severity_filter]
        
        # Sort by severity and confidence
        severity_order = [InsightSeverity.CRITICAL, InsightSeverity.HIGH, InsightSeverity.MEDIUM, InsightSeverity.LOW, InsightSeverity.INFO]
        insights.sort(key=lambda x: (severity_order.index(x.severity), -x.confidence_score))
        
        return insights
    
    def get_bot_rankings(self, metric: AnalyticsMetric, limit: int = 10) -> List[Dict[str, Any]]:
        """Get bot performance rankings for a specific metric"""
        bot_scores = {}
        
        # Calculate average score for each bot
        for dp in self.data_points:
            if dp.metric == metric and dp.bot_id:
                if dp.bot_id not in bot_scores:
                    bot_scores[dp.bot_id] = []
                bot_scores[dp.bot_id].append(dp.value)
        
        # Calculate averages and rank
        rankings = []
        for bot_id, scores in bot_scores.items():
            avg_score = statistics.mean(scores)
            rankings.append({
                "bot_id": bot_id,
                "average_score": avg_score,
                "data_points": len(scores),
                "std_dev": statistics.stdev(scores) if len(scores) > 1 else 0,
                "min_score": min(scores),
                "max_score": max(scores)
            })
        
        # Sort by average score (higher is better for most metrics)
        rankings.sort(key=lambda x: x["average_score"], reverse=True)
        
        return rankings[:limit]
    
    def generate_dashboard_data(self) -> Dict[str, Any]:
        """Generate comprehensive dashboard data"""
        dashboard_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_data_points": len(self.data_points),
                "active_bots": len(set(dp.bot_id for dp in self.data_points if dp.bot_id)),
                "insights_generated": len(self.insights),
                "critical_insights": len([i for i in self.insights.values() if i.severity == InsightSeverity.CRITICAL])
            },
            "recent_trends": {},
            "top_performers": {},
            "anomalies": {},
            "recommendations": []
        }
        
        # Get recent trends for key metrics
        key_metrics = [AnalyticsMetric.TASK_COMPLETION_RATE, AnalyticsMetric.AVERAGE_EXECUTION_TIME, AnalyticsMetric.COST_EFFICIENCY]
        for metric in key_metrics:
            dashboard_data["recent_trends"][metric.value] = self.get_performance_trends(metric, timedelta(days=1))
        
        # Get top performers
        for metric in key_metrics:
            dashboard_data["top_performers"][metric.value] = self.get_bot_rankings(metric, limit=5)
        
        # Get recent anomalies
        for metric in key_metrics:
            anomalies = self.detect_anomalies(metric, lookback_hours=6)
            if anomalies:
                dashboard_data["anomalies"][metric.value] = anomalies[-5:]  # Last 5 anomalies
        
        # Get top recommendations
        high_confidence_insights = [i for i in self.insights.values() if i.confidence_score > 0.7]
        for insight in high_confidence_insights[:5]:
            dashboard_data["recommendations"].extend(insight.recommendations)
        
        return dashboard_data
    
    def _analytics_processor(self):
        """Background analytics processing"""
        while self.running:
            try:
                # Update bot profiles
                bot_ids = set(dp.bot_id for dp in self.data_points if dp.bot_id)
                for bot_id in bot_ids:
                    profile = self._calculate_bot_profile(bot_id)
                    if profile:
                        self.bot_profiles[bot_id] = profile
                
                # Clean up old data
                cutoff_time = datetime.now() - timedelta(days=self.data_retention_days)
                self.data_points = deque([
                    dp for dp in self.data_points if dp.timestamp > cutoff_time
                ], maxlen=10000)
                
                # Sleep for 5 minutes
                import time
                time.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in analytics processor: {e}")
                import time
                time.sleep(60)
    
    def _insights_generator(self):
        """Background insights generation"""
        while self.running:
            try:
                # Generate new insights
                self._generate_performance_insights()
                self._generate_anomaly_insights()
                self._generate_optimization_insights()
                
                # Clean up expired insights
                current_time = datetime.now()
                expired_insights = [
                    insight_id for insight_id, insight in self.insights.items()
                    if insight.expires_at and insight.expires_at < current_time
                ]
                
                for insight_id in expired_insights:
                    del self.insights[insight_id]
                
                # Sleep for 10 minutes
                import time
                time.sleep(600)
                
            except Exception as e:
                logger.error(f"Error in insights generator: {e}")
                import time
                time.sleep(300)
    
    def _trigger_real_time_analysis(self):
        """Trigger real-time analysis for immediate insights"""
        try:
            # Quick anomaly check on recent data
            recent_points = list(self.data_points)[-50:]  # Last 50 points
            
            if len(recent_points) >= 10:
                for metric in AnalyticsMetric:
                    metric_points = [dp for dp in recent_points if dp.metric == metric]
                    if len(metric_points) >= 5:
                        anomalies = self.detect_anomalies(metric, lookback_hours=1)
                        if anomalies:
                            self._create_anomaly_insight(metric, anomalies)
        
        except Exception as e:
            logger.error(f"Error in real-time analysis: {e}")
    
    def _calculate_bot_profile(self, bot_id: str) -> Optional[BotPerformanceProfile]:
        """Calculate comprehensive bot performance profile"""
        bot_data = [dp for dp in self.data_points if dp.bot_id == bot_id]
        
        if not bot_data:
            return None
        
        profile = BotPerformanceProfile(bot_id=bot_id)
        
        # Calculate core metrics
        task_completion_points = [dp for dp in bot_data if dp.metric == AnalyticsMetric.TASK_COMPLETION_RATE]
        if task_completion_points:
            profile.success_rate = statistics.mean([dp.value for dp in task_completion_points])
            profile.total_tasks_completed = len(task_completion_points)
        
        execution_time_points = [dp for dp in bot_data if dp.metric == AnalyticsMetric.AVERAGE_EXECUTION_TIME]
        if execution_time_points:
            profile.average_execution_time = statistics.mean([dp.value for dp in execution_time_points])
        
        cost_efficiency_points = [dp for dp in bot_data if dp.metric == AnalyticsMetric.COST_EFFICIENCY]
        if cost_efficiency_points:
            profile.cost_efficiency = statistics.mean([dp.value for dp in cost_efficiency_points])
        
        quality_points = [dp for dp in bot_data if dp.metric == AnalyticsMetric.QUALITY_SCORE]
        if quality_points:
            profile.quality_score = statistics.mean([dp.value for dp in quality_points])
        
        # Calculate temporal patterns
        hourly_performance = defaultdict(list)
        for dp in bot_data:
            hour = dp.timestamp.hour
            hourly_performance[hour].append(dp.value)
        
        # Find peak performance hours (top 3 hours with highest average performance)
        hour_averages = {hour: statistics.mean(values) for hour, values in hourly_performance.items()}
        profile.peak_performance_hours = sorted(hour_averages.keys(), key=hour_averages.get, reverse=True)[:3]
        
        # Calculate performance trend
        if len(bot_data) > 10:
            recent_performance = statistics.mean([dp.value for dp in bot_data[-10:]])
            older_performance = statistics.mean([dp.value for dp in bot_data[:10]])
            
            if recent_performance > older_performance * 1.1:
                profile.performance_trend = "improving"
            elif recent_performance < older_performance * 0.9:
                profile.performance_trend = "declining"
            else:
                profile.performance_trend = "stable"
        
        # Detect recent anomalies
        profile.recent_anomalies = self.detect_anomalies(
            AnalyticsMetric.TASK_COMPLETION_RATE, 
            bot_id=bot_id, 
            lookback_hours=24
        )
        
        return profile
    
    def _generate_performance_insights(self):
        """Generate performance-based insights"""
        for bot_id, profile in self.bot_profiles.items():
            # Low success rate insight
            if profile.success_rate < 0.7:
                insight = PerformanceInsight(
                    insight_id=str(uuid.uuid4()),
                    insight_type=InsightType.PERFORMANCE_TREND,
                    severity=InsightSeverity.HIGH,
                    title=f"Low Success Rate for {bot_id}",
                    description=f"Bot {bot_id} has a success rate of {profile.success_rate:.1%}, which is below the recommended threshold of 70%.",
                    affected_entities=[bot_id],
                    metrics_involved=[AnalyticsMetric.TASK_COMPLETION_RATE],
                    confidence_score=0.9,
                    supporting_data={"success_rate": profile.success_rate, "tasks_completed": profile.total_tasks_completed},
                    recommendations=[
                        f"Review and improve {bot_id}'s task execution algorithms",
                        f"Consider additional training data for {bot_id}",
                        f"Analyze failed tasks to identify common patterns"
                    ],
                    created_at=datetime.now(),
                    expires_at=datetime.now() + timedelta(days=7)
                )
                
                self.insights[insight.insight_id] = insight
                self._persist_insight(insight)
    
    def _generate_anomaly_insights(self):
        """Generate anomaly-based insights"""
        for metric in AnalyticsMetric:
            anomalies = self.detect_anomalies(metric, lookback_hours=24)
            if len(anomalies) > 3:  # Multiple anomalies indicate a pattern
                self._create_anomaly_insight(metric, anomalies)
    
    def _create_anomaly_insight(self, metric: AnalyticsMetric, anomalies: List[Dict[str, Any]]):
        """Create insight for detected anomalies"""
        affected_bots = list(set([a.get("bot_id") for a in anomalies if a.get("bot_id")]))
        
        insight = PerformanceInsight(
            insight_id=str(uuid.uuid4()),
            insight_type=InsightType.ANOMALY_DETECTION,
            severity=InsightSeverity.MEDIUM,
            title=f"Anomalies Detected in {metric.value.replace('_', ' ').title()}",
            description=f"Multiple anomalous values detected for {metric.value} in the last 24 hours. This may indicate system issues or unusual workload patterns.",
            affected_entities=affected_bots,
            metrics_involved=[metric],
            confidence_score=0.8,
            supporting_data={"anomaly_count": len(anomalies), "anomalies": anomalies},
            recommendations=[
                f"Investigate the root cause of {metric.value} anomalies",
                "Check for system resource constraints",
                "Review recent changes that might affect performance"
            ],
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=3)
        )
        
        self.insights[insight.insight_id] = insight
        self._persist_insight(insight)
    
    def _generate_optimization_insights(self):
        """Generate optimization opportunity insights"""
        # Identify underutilized bots
        bot_utilization = {}
        
        for dp in self.data_points:
            if dp.bot_id and dp.metric == AnalyticsMetric.BOT_UTILIZATION:
                if dp.bot_id not in bot_utilization:
                    bot_utilization[dp.bot_id] = []
                bot_utilization[dp.bot_id].append(dp.value)
        
        for bot_id, utilization_values in bot_utilization.items():
            avg_utilization = statistics.mean(utilization_values)
            
            if avg_utilization < 0.3:  # Less than 30% utilization
                insight = PerformanceInsight(
                    insight_id=str(uuid.uuid4()),
                    insight_type=InsightType.OPTIMIZATION_OPPORTUNITY,
                    severity=InsightSeverity.LOW,
                    title=f"Low Utilization for {bot_id}",
                    description=f"Bot {bot_id} has an average utilization of {avg_utilization:.1%}, indicating potential for increased workload.",
                    affected_entities=[bot_id],
                    metrics_involved=[AnalyticsMetric.BOT_UTILIZATION],
                    confidence_score=0.7,
                    supporting_data={"average_utilization": avg_utilization},
                    recommendations=[
                        f"Consider assigning more tasks to {bot_id}",
                        f"Review {bot_id}'s capabilities for additional task types",
                        "Optimize workload distribution across bots"
                    ],
                    created_at=datetime.now(),
                    expires_at=datetime.now() + timedelta(days=14)
                )
                
                self.insights[insight.insight_id] = insight
                self._persist_insight(insight)
    
    def _persist_data_point(self, data_point: DataPoint):
        """Persist data point to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO data_points (timestamp, metric, value, bot_id, task_id, session_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data_point.timestamp.isoformat(),
                data_point.metric.value,
                data_point.value,
                data_point.bot_id,
                data_point.task_id,
                data_point.session_id,
                json.dumps(data_point.metadata)
            ))
    
    def _persist_bot_profile(self, profile: BotPerformanceProfile):
        """Persist bot profile to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO bot_profiles (bot_id, profile_data, updated_at)
                VALUES (?, ?, ?)
            """, (
                profile.bot_id,
                json.dumps(asdict(profile)),
                datetime.now().isoformat()
            ))
    
    def _persist_insight(self, insight: PerformanceInsight):
        """Persist insight to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO insights (
                    insight_id, insight_type, severity, title, description,
                    affected_entities, metrics_involved, confidence_score,
                    supporting_data, recommendations, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                insight.insight_id,
                insight.insight_type.value,
                insight.severity.value,
                insight.title,
                insight.description,
                json.dumps(insight.affected_entities),
                json.dumps([m.value for m in insight.metrics_involved]),
                insight.confidence_score,
                json.dumps(insight.supporting_data),
                json.dumps(insight.recommendations),
                insight.created_at.isoformat(),
                insight.expires_at.isoformat() if insight.expires_at else None
            ))


# Convenience functions
def create_performance_analyzer() -> PerformanceAnalyzer:
    """Create performance analyzer with default settings"""
    return PerformanceAnalyzer()

def record_bot_metric(analyzer: PerformanceAnalyzer, bot_id: str, metric: AnalyticsMetric, value: float):
    """Convenience function to record bot performance metric"""
    analyzer.record_data_point(metric, value, bot_id=bot_id)

def get_bot_dashboard(analyzer: PerformanceAnalyzer, bot_id: str) -> Dict[str, Any]:
    """Get comprehensive dashboard data for a specific bot"""
    profile = analyzer.get_bot_performance_profile(bot_id)
    trends = {}
    
    key_metrics = [AnalyticsMetric.TASK_COMPLETION_RATE, AnalyticsMetric.AVERAGE_EXECUTION_TIME]
    for metric in key_metrics:
        trends[metric.value] = analyzer.get_performance_trends(metric, bot_id=bot_id)
    
    anomalies = {}
    for metric in key_metrics:
        anomalies[metric.value] = analyzer.detect_anomalies(metric, bot_id=bot_id)
    
    return {
        "bot_id": bot_id,
        "profile": asdict(profile) if profile else None,
        "trends": trends,
        "anomalies": anomalies,
        "recent_insights": [
            asdict(insight) for insight in analyzer.get_insights()
            if bot_id in insight.affected_entities
        ]
    }