import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import json
import sqlite3
from pathlib import Path
import numpy as np
from collections import defaultdict, deque
import statistics
from scipy import stats
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class InsightType(Enum):
    PERFORMANCE = "performance"
    RESOURCE_OPTIMIZATION = "resource_optimization"
    ANOMALY = "anomaly"
    TREND = "trend"
    PREDICTION = "prediction"
    COST_OPTIMIZATION = "cost_optimization"
    EFFICIENCY = "efficiency"
    RELIABILITY = "reliability"

class InsightPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class InsightCategory(Enum):
    OPERATIONAL = "operational"
    STRATEGIC = "strategic"
    TACTICAL = "tactical"
    ALERT = "alert"

@dataclass
class Insight:
    id: str
    type: InsightType
    priority: InsightPriority
    category: InsightCategory
    title: str
    description: str
    impact: str
    recommendation: str
    confidence: float
    data_points: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.type.value,
            'priority': self.priority.value,
            'category': self.category.value,
            'title': self.title,
            'description': self.description,
            'impact': self.impact,
            'recommendation': self.recommendation,
            'confidence': self.confidence,
            'data_points': self.data_points,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }

@dataclass
class AnalyticsRule:
    id: str
    name: str
    description: str
    rule_type: str
    condition: str  # Python expression
    threshold: float
    window_minutes: int
    enabled: bool = True
    insight_template: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

class TrendAnalyzer:
    """Analyze trends in time series data"""
    
    def __init__(self):
        self.trend_cache = {}
        self.seasonal_cache = {}
    
    def analyze_trend(
        self, 
        data: List[Tuple[datetime, float]], 
        metric_name: str,
        min_points: int = 10
    ) -> Dict[str, Any]:
        """Analyze trend in time series data"""
        try:
            if len(data) < min_points:
                return {'trend': 'insufficient_data', 'confidence': 0.0}
            
            # Sort by timestamp
            sorted_data = sorted(data, key=lambda x: x[0])
            
            # Extract values
            timestamps = [(point[0] - sorted_data[0][0]).total_seconds() / 3600 for point in sorted_data]  # Hours
            values = [point[1] for point in sorted_data]
            
            # Linear regression for trend
            slope, intercept, r_value, p_value, std_err = stats.linregress(timestamps, values)
            
            # Determine trend direction
            if abs(slope) < std_err * 2:  # Not statistically significant
                trend = 'stable'
                confidence = max(0.0, 1.0 - p_value)
            elif slope > 0:
                trend = 'increasing'
                confidence = max(0.0, 1.0 - p_value)
            else:
                trend = 'decreasing'
                confidence = max(0.0, 1.0 - p_value)
            
            # Calculate trend strength
            strength = abs(slope) / (np.std(values) + 1e-6)
            
            # Seasonal analysis
            seasonal_info = self._analyze_seasonality(sorted_data)
            
            result = {
                'trend': trend,
                'slope': slope,
                'confidence': confidence,
                'strength': strength,
                'r_squared': r_value ** 2,
                'p_value': p_value,
                'seasonality': seasonal_info,
                'data_points': len(data),
                'time_span_hours': timestamps[-1] if timestamps else 0
            }
            
            # Cache result
            cache_key = f"{metric_name}_{len(data)}"
            self.trend_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Trend analysis failed for {metric_name}: {e}")
            return {'trend': 'error', 'confidence': 0.0, 'error': str(e)}
    
    def _analyze_seasonality(self, data: List[Tuple[datetime, float]]) -> Dict[str, Any]:
        """Analyze seasonal patterns"""
        try:
            if len(data) < 48:  # Need at least 48 hours of data
                return {'detected': False}
            
            # Group by hour of day
            hourly_data = defaultdict(list)
            for timestamp, value in data:
                hour = timestamp.hour
                hourly_data[hour].append(value)
            
            # Calculate hourly averages
            hourly_averages = {hour: np.mean(values) for hour, values in hourly_data.items()}
            
            if len(hourly_averages) < 12:  # Need data for at least half the day
                return {'detected': False}
            
            # Check for significant hourly variation
            all_hourly_values = list(hourly_averages.values())
            hourly_variation = np.std(all_hourly_values) / (np.mean(all_hourly_values) + 1e-6)
            
            seasonal_detected = hourly_variation > 0.2  # 20% coefficient of variation
            
            # Identify peak and low hours
            if seasonal_detected:
                peak_hour = max(hourly_averages, key=hourly_averages.get)
                low_hour = min(hourly_averages, key=hourly_averages.get)
                
                return {
                    'detected': True,
                    'hourly_variation': hourly_variation,
                    'peak_hour': peak_hour,
                    'low_hour': low_hour,
                    'hourly_averages': hourly_averages
                }
            
            return {'detected': False, 'hourly_variation': hourly_variation}
            
        except Exception as e:
            logger.error(f"Seasonality analysis failed: {e}")
            return {'detected': False, 'error': str(e)}
    
    def detect_change_points(
        self, 
        data: List[Tuple[datetime, float]], 
        sensitivity: float = 2.0
    ) -> List[Dict[str, Any]]:
        """Detect significant change points in time series"""
        try:
            if len(data) < 20:
                return []
            
            sorted_data = sorted(data, key=lambda x: x[0])
            values = [point[1] for point in sorted_data]
            timestamps = [point[0] for point in sorted_data]
            
            change_points = []
            window_size = min(10, len(values) // 4)
            
            for i in range(window_size, len(values) - window_size):
                # Compare before and after windows
                before_window = values[i-window_size:i]
                after_window = values[i:i+window_size]
                
                # Statistical test for significant change
                t_stat, p_value = stats.ttest_ind(before_window, after_window)
                
                if p_value < 0.05 / len(values):  # Bonferroni correction
                    change_magnitude = abs(np.mean(after_window) - np.mean(before_window))
                    change_direction = 'increase' if np.mean(after_window) > np.mean(before_window) else 'decrease'
                    
                    change_points.append({
                        'timestamp': timestamps[i],
                        'index': i,
                        'direction': change_direction,
                        'magnitude': change_magnitude,
                        'significance': 1 - p_value,
                        'before_mean': np.mean(before_window),
                        'after_mean': np.mean(after_window)
                    })
            
            return change_points
            
        except Exception as e:
            logger.error(f"Change point detection failed: {e}")
            return []

class AnomalyDetector:
    """Detect anomalies in system metrics"""
    
    def __init__(self):
        self.models = {}
        self.thresholds = {}
        self.history = defaultdict(lambda: deque(maxlen=1000))
    
    def detect_anomalies(
        self, 
        data: List[Tuple[datetime, float]], 
        metric_name: str,
        method: str = "statistical"
    ) -> List[Dict[str, Any]]:
        """Detect anomalies in time series data"""
        try:
            if len(data) < 10:
                return []
            
            if method == "statistical":
                return self._statistical_anomaly_detection(data, metric_name)
            elif method == "isolation_forest":
                return self._isolation_forest_detection(data, metric_name)
            elif method == "clustering":
                return self._clustering_anomaly_detection(data, metric_name)
            else:
                return self._statistical_anomaly_detection(data, metric_name)
                
        except Exception as e:
            logger.error(f"Anomaly detection failed for {metric_name}: {e}")
            return []
    
    def _statistical_anomaly_detection(
        self, 
        data: List[Tuple[datetime, float]], 
        metric_name: str
    ) -> List[Dict[str, Any]]:
        """Statistical anomaly detection using z-score and IQR"""
        anomalies = []
        
        sorted_data = sorted(data, key=lambda x: x[0])
        values = [point[1] for point in sorted_data]
        timestamps = [point[0] for point in sorted_data]
        
        # Calculate statistics
        mean_val = np.mean(values)
        std_val = np.std(values)
        q1, q3 = np.percentile(values, [25, 75])
        iqr = q3 - q1
        
        # Z-score based detection
        z_threshold = 3.0
        iqr_threshold = 1.5
        
        for i, (timestamp, value) in enumerate(zip(timestamps, values)):
            z_score = abs(value - mean_val) / (std_val + 1e-6)
            iqr_outlier = value < (q1 - iqr_threshold * iqr) or value > (q3 + iqr_threshold * iqr)
            
            if z_score > z_threshold or iqr_outlier:
                anomaly_type = "extreme" if z_score > 4.0 else "moderate"
                
                anomalies.append({
                    'timestamp': timestamp,
                    'value': value,
                    'anomaly_score': z_score,
                    'anomaly_type': anomaly_type,
                    'method': 'statistical',
                    'expected_range': (mean_val - 2*std_val, mean_val + 2*std_val),
                    'deviation_magnitude': abs(value - mean_val) / (std_val + 1e-6)
                })
        
        return anomalies
    
    def _clustering_anomaly_detection(
        self, 
        data: List[Tuple[datetime, float]], 
        metric_name: str
    ) -> List[Dict[str, Any]]:
        """Clustering-based anomaly detection using DBSCAN"""
        try:
            if len(data) < 20:
                return []
            
            sorted_data = sorted(data, key=lambda x: x[0])
            
            # Prepare features: [value, time_since_start_hours, hour_of_day]
            start_time = sorted_data[0][0]
            features = []
            
            for timestamp, value in sorted_data:
                time_since_start = (timestamp - start_time).total_seconds() / 3600
                hour_of_day = timestamp.hour
                features.append([value, time_since_start, hour_of_day])
            
            features_array = np.array(features)
            
            # Normalize features
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features_array)
            
            # DBSCAN clustering
            eps = 0.5
            min_samples = max(2, len(data) // 20)
            
            dbscan = DBSCAN(eps=eps, min_samples=min_samples)
            labels = dbscan.fit_predict(features_scaled)
            
            # Identify anomalies (points labeled as -1)
            anomalies = []
            for i, label in enumerate(labels):
                if label == -1:  # Anomaly
                    timestamp, value = sorted_data[i]
                    
                    # Calculate anomaly score based on distance to nearest cluster
                    distances = []
                    for j, other_label in enumerate(labels):
                        if other_label != -1:
                            dist = np.linalg.norm(features_scaled[i] - features_scaled[j])
                            distances.append(dist)
                    
                    anomaly_score = min(distances) if distances else 1.0
                    
                    anomalies.append({
                        'timestamp': timestamp,
                        'value': value,
                        'anomaly_score': anomaly_score,
                        'anomaly_type': 'cluster_outlier',
                        'method': 'clustering',
                        'cluster_label': int(label)
                    })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Clustering anomaly detection failed: {e}")
            return []

class InsightsEngine:
    """Main insights and analytics engine"""
    
    def __init__(self, db_path: str = "/home/activeloguser/activelog/data/insights.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.trend_analyzer = TrendAnalyzer()
        self.anomaly_detector = AnomalyDetector()
        
        self.running = False
        self.analytics_rules = []
        self.insights_cache = deque(maxlen=1000)
        self.data_sources = {}
        
        # Analysis intervals
        self.analysis_intervals = {
            'real_time': 60,      # 1 minute
            'short_term': 900,    # 15 minutes
            'medium_term': 3600,  # 1 hour
            'long_term': 86400    # 1 day
        }
        
        self._init_database()
        self._load_analytics_rules()
        
        # Background tasks
        self._analysis_tasks = []
    
    def _init_database(self):
        """Initialize insights database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS insights (
                    id TEXT PRIMARY KEY,
                    type TEXT,
                    priority INTEGER,
                    category TEXT,
                    title TEXT,
                    description TEXT,
                    impact TEXT,
                    recommendation TEXT,
                    confidence REAL,
                    data_points TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    acknowledged BOOLEAN DEFAULT FALSE,
                    action_taken TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analytics_rules (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    rule_type TEXT,
                    condition_expr TEXT,
                    threshold REAL,
                    window_minutes INTEGER,
                    enabled BOOLEAN DEFAULT TRUE,
                    insight_template TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_triggered TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metric_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT,
                    metric_name TEXT,
                    timestamp TIMESTAMP,
                    value REAL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    def _load_analytics_rules(self):
        """Load analytics rules from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, name, description, rule_type, condition_expr, 
                           threshold, window_minutes, enabled, insight_template
                    FROM analytics_rules
                    WHERE enabled = TRUE
                """)
                
                for row in cursor.fetchall():
                    rule = AnalyticsRule(
                        id=row[0],
                        name=row[1],
                        description=row[2],
                        rule_type=row[3],
                        condition=row[4],
                        threshold=row[5],
                        window_minutes=row[6],
                        enabled=row[7],
                        insight_template=json.loads(row[8]) if row[8] else {}
                    )
                    self.analytics_rules.append(rule)
            
            # Add default rules if none exist
            if not self.analytics_rules:
                self._create_default_rules()
            
            logger.info(f"Loaded {len(self.analytics_rules)} analytics rules")
            
        except Exception as e:
            logger.error(f"Failed to load analytics rules: {e}")
    
    def _create_default_rules(self):
        """Create default analytics rules"""
        default_rules = [
            AnalyticsRule(
                id="high_cpu_usage",
                name="High CPU Usage",
                description="Detect sustained high CPU utilization",
                rule_type="threshold",
                condition="cpu_utilization > threshold",
                threshold=85.0,
                window_minutes=15,
                insight_template={
                    'title': 'High CPU Usage Detected',
                    'impact': 'Performance degradation and potential service slowdown',
                    'recommendation': 'Consider scaling up resources or optimizing CPU-intensive tasks'
                }
            ),
            AnalyticsRule(
                id="memory_leak_detection",
                name="Memory Leak Detection",
                description="Detect continuously increasing memory usage",
                rule_type="trend",
                condition="memory_trend_slope > threshold and trend_confidence > 0.7",
                threshold=5.0,  # MB per hour
                window_minutes=60,
                insight_template={
                    'title': 'Potential Memory Leak Detected',
                    'impact': 'System instability and potential crashes',
                    'recommendation': 'Investigate memory usage patterns and check for leaks'
                }
            ),
            AnalyticsRule(
                id="task_queue_backlog",
                name="Task Queue Backlog",
                description="Detect growing task queue",
                rule_type="threshold",
                condition="queue_length > threshold",
                threshold=50.0,
                window_minutes=10,
                insight_template={
                    'title': 'Task Queue Backlog Building Up',
                    'impact': 'Increased processing delays and potential timeout issues',
                    'recommendation': 'Scale up processing capacity or optimize task processing'
                }
            ),
            AnalyticsRule(
                id="error_rate_spike",
                name="Error Rate Spike",
                description="Detect sudden increase in error rate",
                rule_type="anomaly",
                condition="error_rate_anomaly_score > threshold",
                threshold=2.0,
                window_minutes=5,
                insight_template={
                    'title': 'Error Rate Spike Detected',
                    'impact': 'Service degradation and user experience issues',
                    'recommendation': 'Investigate error logs and check system health'
                }
            ),
            AnalyticsRule(
                id="performance_degradation",
                name="Performance Degradation",
                description="Detect decreasing throughput trends",
                rule_type="trend",
                condition="throughput_trend_slope < -threshold and trend_confidence > 0.6",
                threshold=10.0,  # requests per minute decrease
                window_minutes=30,
                insight_template={
                    'title': 'Performance Degradation Trend',
                    'impact': 'Reduced system efficiency and capacity',
                    'recommendation': 'Analyze performance bottlenecks and optimize system resources'
                }
            )
        ]
        
        for rule in default_rules:
            self.add_analytics_rule(rule)
    
    async def start(self):
        """Start the insights engine"""
        try:
            logger.info("Starting Insights Engine...")
            
            self.running = True
            
            # Start analysis tasks
            for interval_name, interval_seconds in self.analysis_intervals.items():
                task = asyncio.create_task(self._analysis_loop(interval_name, interval_seconds))
                self._analysis_tasks.append(task)
            
            logger.info("Insights Engine started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Insights Engine: {e}")
            raise
    
    async def stop(self):
        """Stop the insights engine"""
        logger.info("Stopping Insights Engine...")
        
        self.running = False
        
        # Cancel analysis tasks
        for task in self._analysis_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self._analysis_tasks.clear()
        
        logger.info("Insights Engine stopped")
    
    async def _analysis_loop(self, interval_name: str, interval_seconds: int):
        """Main analysis loop for different time intervals"""
        while self.running:
            try:
                await self._run_analysis(interval_name)
                await asyncio.sleep(interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in {interval_name} analysis loop: {e}")
                await asyncio.sleep(min(interval_seconds, 300))  # Max 5 minute backoff
    
    async def _run_analysis(self, interval_name: str):
        """Run analysis for specific time interval"""
        try:
            # Get time window for analysis
            now = datetime.now()
            if interval_name == 'real_time':
                start_time = now - timedelta(minutes=5)
            elif interval_name == 'short_term':
                start_time = now - timedelta(hours=1)
            elif interval_name == 'medium_term':
                start_time = now - timedelta(hours=6)
            else:  # long_term
                start_time = now - timedelta(days=1)
            
            # Get data for analysis
            metric_data = await self._get_metric_data(start_time, now)
            
            if not metric_data:
                return
            
            # Run different types of analysis
            await self._analyze_trends(metric_data, interval_name)
            await self._detect_anomalies(metric_data, interval_name)
            await self._check_analytics_rules(metric_data, interval_name)
            await self._generate_efficiency_insights(metric_data, interval_name)
            
        except Exception as e:
            logger.error(f"Analysis failed for {interval_name}: {e}")
    
    async def _get_metric_data(self, start_time: datetime, end_time: datetime) -> Dict[str, List[Tuple[datetime, float]]]:
        """Get metric data from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT source, metric_name, timestamp, value
                    FROM metric_data
                    WHERE timestamp BETWEEN ? AND ?
                    ORDER BY timestamp
                """, (start_time, end_time))
                
                metric_data = defaultdict(list)
                for row in cursor.fetchall():
                    source, metric_name, timestamp_str, value = row
                    timestamp = datetime.fromisoformat(timestamp_str) if isinstance(timestamp_str, str) else timestamp_str
                    key = f"{source}.{metric_name}"
                    metric_data[key].append((timestamp, value))
                
                return dict(metric_data)
                
        except Exception as e:
            logger.error(f"Failed to get metric data: {e}")
            return {}
    
    async def _analyze_trends(self, metric_data: Dict[str, List[Tuple[datetime, float]]], interval_name: str):
        """Analyze trends in metric data"""
        for metric_name, data_points in metric_data.items():
            if len(data_points) < 5:
                continue
            
            try:
                trend_result = self.trend_analyzer.analyze_trend(data_points, metric_name)
                
                # Generate insights for significant trends
                if trend_result['confidence'] > 0.7 and trend_result['strength'] > 0.1:
                    await self._generate_trend_insight(metric_name, trend_result, data_points, interval_name)
                
                # Detect change points
                change_points = self.trend_analyzer.detect_change_points(data_points)
                for change_point in change_points:
                    await self._generate_change_point_insight(metric_name, change_point, interval_name)
                    
            except Exception as e:
                logger.error(f"Trend analysis failed for {metric_name}: {e}")
    
    async def _detect_anomalies(self, metric_data: Dict[str, List[Tuple[datetime, float]]], interval_name: str):
        """Detect anomalies in metric data"""
        for metric_name, data_points in metric_data.items():
            if len(data_points) < 10:
                continue
            
            try:
                anomalies = self.anomaly_detector.detect_anomalies(data_points, metric_name)
                
                for anomaly in anomalies:
                    await self._generate_anomaly_insight(metric_name, anomaly, interval_name)
                    
            except Exception as e:
                logger.error(f"Anomaly detection failed for {metric_name}: {e}")
    
    async def _check_analytics_rules(self, metric_data: Dict[str, List[Tuple[datetime, float]]], interval_name: str):
        """Check analytics rules against current data"""
        for rule in self.analytics_rules:
            if not rule.enabled:
                continue
            
            try:
                triggered = await self._evaluate_rule(rule, metric_data)
                if triggered:
                    await self._generate_rule_insight(rule, metric_data, interval_name)
                    
            except Exception as e:
                logger.error(f"Rule evaluation failed for {rule.name}: {e}")
    
    async def _evaluate_rule(self, rule: AnalyticsRule, metric_data: Dict[str, List[Tuple[datetime, float]]]) -> bool:
        """Evaluate if analytics rule is triggered"""
        try:
            # Create evaluation context
            context = {'threshold': rule.threshold}
            
            # Extract relevant metrics
            for metric_key, data_points in metric_data.items():
                if not data_points:
                    continue
                
                # Get metric base name (remove source prefix)
                metric_name = metric_key.split('.')[-1]
                
                # Latest value
                context[metric_name] = data_points[-1][1]
                
                # Average over window
                window_start = datetime.now() - timedelta(minutes=rule.window_minutes)
                window_data = [val for ts, val in data_points if ts >= window_start]
                if window_data:
                    context[f"{metric_name}_avg"] = np.mean(window_data)
                    context[f"{metric_name}_max"] = np.max(window_data)
                    context[f"{metric_name}_min"] = np.min(window_data)
                
                # Trend analysis for trend rules
                if rule.rule_type == 'trend' and len(data_points) >= 10:
                    trend_result = self.trend_analyzer.analyze_trend(data_points, metric_name)
                    context[f"{metric_name}_trend_slope"] = trend_result.get('slope', 0)
                    context[f"trend_confidence"] = trend_result.get('confidence', 0)
                
                # Anomaly analysis for anomaly rules
                if rule.rule_type == 'anomaly' and len(data_points) >= 10:
                    anomalies = self.anomaly_detector.detect_anomalies(data_points, metric_name)
                    if anomalies:
                        latest_anomaly = max(anomalies, key=lambda a: a['timestamp'])
                        context[f"{metric_name}_anomaly_score"] = latest_anomaly['anomaly_score']
                    else:
                        context[f"{metric_name}_anomaly_score"] = 0
            
            # Evaluate condition
            try:
                result = eval(rule.condition, {"__builtins__": {}}, context)
                return bool(result)
            except Exception as eval_error:
                logger.error(f"Rule condition evaluation failed for {rule.name}: {eval_error}")
                return False
                
        except Exception as e:
            logger.error(f"Rule evaluation error for {rule.name}: {e}")
            return False
    
    async def _generate_efficiency_insights(self, metric_data: Dict[str, List[Tuple[datetime, float]]], interval_name: str):
        """Generate efficiency and optimization insights"""
        try:
            # Resource efficiency analysis
            cpu_data = metric_data.get('system.cpu_utilization', [])
            memory_data = metric_data.get('system.memory_utilization', [])
            throughput_data = metric_data.get('system.throughput', [])
            
            if cpu_data and memory_data and throughput_data:
                # Calculate resource efficiency
                avg_cpu = np.mean([val for _, val in cpu_data])
                avg_memory = np.mean([val for _, val in memory_data])
                avg_throughput = np.mean([val for _, val in throughput_data])
                
                # Efficiency score (throughput per resource unit)
                resource_usage = (avg_cpu + avg_memory) / 2
                if resource_usage > 0:
                    efficiency_score = avg_throughput / resource_usage
                    
                    # Compare with historical efficiency
                    if efficiency_score < 0.5:  # Low efficiency threshold
                        await self._create_insight(
                            id=f"low_efficiency_{interval_name}",
                            type=InsightType.EFFICIENCY,
                            priority=InsightPriority.MEDIUM,
                            category=InsightCategory.OPERATIONAL,
                            title="Low Resource Efficiency Detected",
                            description=f"System efficiency score is {efficiency_score:.2f}, indicating suboptimal resource utilization",
                            impact="Increased operational costs and reduced system capacity",
                            recommendation="Review resource allocation and consider workload optimization",
                            confidence=0.8,
                            data_points=[
                                {'metric': 'avg_cpu', 'value': avg_cpu},
                                {'metric': 'avg_memory', 'value': avg_memory},
                                {'metric': 'avg_throughput', 'value': avg_throughput},
                                {'metric': 'efficiency_score', 'value': efficiency_score}
                            ]
                        )
            
        except Exception as e:
            logger.error(f"Efficiency analysis failed: {e}")
    
    async def _generate_trend_insight(
        self, 
        metric_name: str, 
        trend_result: Dict[str, Any], 
        data_points: List[Tuple[datetime, float]], 
        interval_name: str
    ):
        """Generate insight for significant trend"""
        try:
            trend = trend_result['trend']
            confidence = trend_result['confidence']
            strength = trend_result['strength']
            
            if trend == 'increasing':
                title = f"Increasing Trend in {metric_name}"
                impact = f"{metric_name} is showing an increasing trend with {confidence:.1%} confidence"
                if 'cpu' in metric_name.lower() or 'memory' in metric_name.lower():
                    recommendation = "Monitor resource usage and consider scaling if trend continues"
                    priority = InsightPriority.MEDIUM
                elif 'error' in metric_name.lower():
                    recommendation = "Investigate root cause of increasing errors"
                    priority = InsightPriority.HIGH
                else:
                    recommendation = "Monitor trend and assess impact on system performance"
                    priority = InsightPriority.LOW
                    
            elif trend == 'decreasing':
                title = f"Decreasing Trend in {metric_name}"
                impact = f"{metric_name} is showing a decreasing trend with {confidence:.1%} confidence"
                if 'throughput' in metric_name.lower() or 'performance' in metric_name.lower():
                    recommendation = "Investigate performance degradation causes"
                    priority = InsightPriority.HIGH
                else:
                    recommendation = "Monitor trend and assess if intervention is needed"
                    priority = InsightPriority.LOW
            else:
                return  # Skip stable trends
            
            await self._create_insight(
                id=f"trend_{metric_name}_{interval_name}_{int(datetime.now().timestamp())}",
                type=InsightType.TREND,
                priority=priority,
                category=InsightCategory.OPERATIONAL,
                title=title,
                description=f"Trend analysis shows {trend} pattern in {metric_name} over {interval_name} interval",
                impact=impact,
                recommendation=recommendation,
                confidence=confidence,
                data_points=[
                    {'metric': 'slope', 'value': trend_result['slope']},
                    {'metric': 'strength', 'value': strength},
                    {'metric': 'r_squared', 'value': trend_result['r_squared']},
                    {'metric': 'data_points_count', 'value': len(data_points)}
                ]
            )
            
        except Exception as e:
            logger.error(f"Failed to generate trend insight: {e}")
    
    async def _generate_anomaly_insight(
        self, 
        metric_name: str, 
        anomaly: Dict[str, Any], 
        interval_name: str
    ):
        """Generate insight for detected anomaly"""
        try:
            anomaly_type = anomaly['anomaly_type']
            score = anomaly['anomaly_score']
            timestamp = anomaly['timestamp']
            value = anomaly['value']
            
            priority = InsightPriority.HIGH if score > 4 else InsightPriority.MEDIUM
            
            title = f"Anomaly Detected in {metric_name}"
            description = f"Unusual value ({value}) detected in {metric_name} at {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            impact = f"Anomalous behavior may indicate system issues or unusual workload patterns"
            
            if anomaly_type == 'extreme':
                recommendation = "Immediate investigation recommended due to extreme deviation"
                priority = InsightPriority.CRITICAL
            else:
                recommendation = "Monitor closely and investigate if pattern continues"
            
            await self._create_insight(
                id=f"anomaly_{metric_name}_{interval_name}_{int(timestamp.timestamp())}",
                type=InsightType.ANOMALY,
                priority=priority,
                category=InsightCategory.ALERT,
                title=title,
                description=description,
                impact=impact,
                recommendation=recommendation,
                confidence=min(score / 5, 1.0),  # Normalize score to confidence
                data_points=[
                    {'metric': 'anomaly_value', 'value': value},
                    {'metric': 'anomaly_score', 'value': score},
                    {'metric': 'anomaly_type', 'value': anomaly_type}
                ],
                expires_at=datetime.now() + timedelta(hours=24)
            )
            
        except Exception as e:
            logger.error(f"Failed to generate anomaly insight: {e}")
    
    async def _generate_change_point_insight(
        self, 
        metric_name: str, 
        change_point: Dict[str, Any], 
        interval_name: str
    ):
        """Generate insight for detected change point"""
        try:
            timestamp = change_point['timestamp']
            direction = change_point['direction']
            magnitude = change_point['magnitude']
            significance = change_point['significance']
            
            title = f"Significant Change Detected in {metric_name}"
            description = f"Detected {direction} of {magnitude:.2f} in {metric_name} at {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            impact = f"Sudden change may indicate system event or configuration modification"
            recommendation = "Correlate with recent system changes or events"
            
            await self._create_insight(
                id=f"change_point_{metric_name}_{interval_name}_{int(timestamp.timestamp())}",
                type=InsightType.ANOMALY,
                priority=InsightPriority.MEDIUM,
                category=InsightCategory.OPERATIONAL,
                title=title,
                description=description,
                impact=impact,
                recommendation=recommendation,
                confidence=significance,
                data_points=[
                    {'metric': 'change_magnitude', 'value': magnitude},
                    {'metric': 'change_direction', 'value': direction},
                    {'metric': 'significance', 'value': significance}
                ],
                expires_at=datetime.now() + timedelta(hours=12)
            )
            
        except Exception as e:
            logger.error(f"Failed to generate change point insight: {e}")
    
    async def _generate_rule_insight(
        self, 
        rule: AnalyticsRule, 
        metric_data: Dict[str, List[Tuple[datetime, float]]], 
        interval_name: str
    ):
        """Generate insight from triggered analytics rule"""
        try:
            template = rule.insight_template
            
            title = template.get('title', f"Rule Triggered: {rule.name}")
            description = template.get('description', rule.description)
            impact = template.get('impact', "System condition requires attention")
            recommendation = template.get('recommendation', "Review system status and take appropriate action")
            
            # Determine priority based on rule type and threshold
            if rule.rule_type == 'anomaly':
                priority = InsightPriority.HIGH
            elif 'critical' in rule.name.lower() or 'error' in rule.name.lower():
                priority = InsightPriority.CRITICAL
            else:
                priority = InsightPriority.MEDIUM
            
            await self._create_insight(
                id=f"rule_{rule.id}_{interval_name}_{int(datetime.now().timestamp())}",
                type=getattr(InsightType, rule.rule_type.upper(), InsightType.PERFORMANCE),
                priority=priority,
                category=InsightCategory.OPERATIONAL,
                title=title,
                description=description,
                impact=impact,
                recommendation=recommendation,
                confidence=0.9,  # Rules have high confidence
                data_points=[
                    {'metric': 'rule_id', 'value': rule.id},
                    {'metric': 'threshold', 'value': rule.threshold},
                    {'metric': 'window_minutes', 'value': rule.window_minutes}
                ],
                expires_at=datetime.now() + timedelta(hours=6)
            )
            
            # Update rule last triggered time
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE analytics_rules 
                    SET last_triggered = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (rule.id,))
                
        except Exception as e:
            logger.error(f"Failed to generate rule insight: {e}")
    
    async def _create_insight(
        self,
        id: str,
        type: InsightType,
        priority: InsightPriority,
        category: InsightCategory,
        title: str,
        description: str,
        impact: str,
        recommendation: str,
        confidence: float,
        data_points: List[Dict[str, Any]] = None,
        metadata: Dict[str, Any] = None,
        expires_at: Optional[datetime] = None
    ):
        """Create and store a new insight"""
        try:
            insight = Insight(
                id=id,
                type=type,
                priority=priority,
                category=category,
                title=title,
                description=description,
                impact=impact,
                recommendation=recommendation,
                confidence=confidence,
                data_points=data_points or [],
                metadata=metadata or {},
                expires_at=expires_at
            )
            
            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO insights 
                    (id, type, priority, category, title, description, impact, 
                     recommendation, confidence, data_points, metadata, 
                     created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    insight.id,
                    insight.type.value,
                    insight.priority.value,
                    insight.category.value,
                    insight.title,
                    insight.description,
                    insight.impact,
                    insight.recommendation,
                    insight.confidence,
                    json.dumps(insight.data_points),
                    json.dumps(insight.metadata),
                    insight.created_at,
                    insight.expires_at
                ))
            
            # Add to cache
            self.insights_cache.append(insight)
            
            logger.info(f"Created insight: {insight.title} (Priority: {insight.priority.name})")
            
        except Exception as e:
            logger.error(f"Failed to create insight: {e}")
    
    async def add_metric_data(
        self, 
        source: str, 
        metric_name: str, 
        value: float, 
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add metric data point for analysis"""
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO metric_data (source, metric_name, timestamp, value, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    source,
                    metric_name,
                    timestamp,
                    value,
                    json.dumps(metadata) if metadata else None
                ))
                
        except Exception as e:
            logger.error(f"Failed to add metric data: {e}")
    
    def add_analytics_rule(self, rule: AnalyticsRule):
        """Add analytics rule"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO analytics_rules 
                    (id, name, description, rule_type, condition_expr, threshold,
                     window_minutes, enabled, insight_template)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rule.id,
                    rule.name,
                    rule.description,
                    rule.rule_type,
                    rule.condition,
                    rule.threshold,
                    rule.window_minutes,
                    rule.enabled,
                    json.dumps(rule.insight_template)
                ))
            
            # Update in-memory rules
            self.analytics_rules = [r for r in self.analytics_rules if r.id != rule.id]
            self.analytics_rules.append(rule)
            
            logger.info(f"Added analytics rule: {rule.name}")
            
        except Exception as e:
            logger.error(f"Failed to add analytics rule: {e}")
    
    def get_insights(
        self, 
        type_filter: Optional[InsightType] = None,
        priority_filter: Optional[InsightPriority] = None,
        category_filter: Optional[InsightCategory] = None,
        limit: int = 50
    ) -> List[Insight]:
        """Get insights with optional filters"""
        try:
            conditions = []
            params = []
            
            if type_filter:
                conditions.append("type = ?")
                params.append(type_filter.value)
            
            if priority_filter:
                conditions.append("priority >= ?")
                params.append(priority_filter.value)
            
            if category_filter:
                conditions.append("category = ?")
                params.append(category_filter.value)
            
            # Only show non-expired insights
            conditions.append("(expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)")
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(f"""
                    SELECT id, type, priority, category, title, description, 
                           impact, recommendation, confidence, data_points, 
                           metadata, created_at, expires_at
                    FROM insights
                    WHERE {where_clause}
                    ORDER BY priority DESC, created_at DESC
                    LIMIT ?
                """, params + [limit])
                
                insights = []
                for row in cursor.fetchall():
                    insight = Insight(
                        id=row[0],
                        type=InsightType(row[1]),
                        priority=InsightPriority(row[2]),
                        category=InsightCategory(row[3]),
                        title=row[4],
                        description=row[5],
                        impact=row[6],
                        recommendation=row[7],
                        confidence=row[8],
                        data_points=json.loads(row[9]) if row[9] else [],
                        metadata=json.loads(row[10]) if row[10] else {},
                        created_at=datetime.fromisoformat(row[11]) if isinstance(row[11], str) else row[11],
                        expires_at=datetime.fromisoformat(row[12]) if row[12] and isinstance(row[12], str) else row[12]
                    )
                    insights.append(insight)
                
                return insights
                
        except Exception as e:
            logger.error(f"Failed to get insights: {e}")
            return []
    
    def acknowledge_insight(self, insight_id: str, action_taken: Optional[str] = None):
        """Acknowledge an insight"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE insights 
                    SET acknowledged = TRUE, action_taken = ?
                    WHERE id = ?
                """, (action_taken, insight_id))
            
            logger.info(f"Acknowledged insight: {insight_id}")
            
        except Exception as e:
            logger.error(f"Failed to acknowledge insight: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get insights engine system status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Count insights by priority
                cursor = conn.execute("""
                    SELECT priority, COUNT(*) 
                    FROM insights
                    WHERE (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                    AND acknowledged = FALSE
                    GROUP BY priority
                """)
                
                insight_counts = {}
                for row in cursor.fetchall():
                    priority_name = InsightPriority(row[0]).name
                    insight_counts[priority_name] = row[1]
                
                # Count analytics rules
                cursor = conn.execute("SELECT COUNT(*) FROM analytics_rules WHERE enabled = TRUE")
                active_rules_count = cursor.fetchone()[0]
                
                # Count recent metric data points
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM metric_data 
                    WHERE created_at > datetime('now', '-1 hour')
                """)
                recent_metrics_count = cursor.fetchone()[0]
            
            return {
                'running': self.running,
                'active_analytics_rules': active_rules_count,
                'recent_metric_points': recent_metrics_count,
                'insights_by_priority': insight_counts,
                'total_cached_insights': len(self.insights_cache),
                'analysis_intervals': list(self.analysis_intervals.keys())
            }
            
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {'running': self.running, 'error': str(e)}