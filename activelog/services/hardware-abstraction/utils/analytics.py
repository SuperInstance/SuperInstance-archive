"""
Advanced Analytics Engine for Hardware Abstraction System
Real-time analytics, performance monitoring, and AI-powered insights
"""

import asyncio
import logging
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = None

@dataclass
class PerformanceTrend:
    """Performance trend analysis"""
    metric_name: str
    current_value: float
    trend_direction: str  # "up", "down", "stable"
    trend_strength: float  # 0-1
    prediction: Optional[float] = None
    confidence: float = 0.0

@dataclass
class DeviceAnalytics:
    """Device analytics summary"""
    device_id: str
    health_score: float
    performance_score: float
    efficiency_rating: str
    usage_hours: float
    data_transferred_gb: float
    commands_executed: int
    error_rate: float
    last_error_time: Optional[datetime] = None

class AnalyticsEngine:
    """Advanced analytics engine for system monitoring and insights"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Time-series data storage (in production, use proper TSDB)
        self.metrics_storage = defaultdict(lambda: defaultdict(deque))  # device_id -> metric_name -> deque
        self.system_metrics = defaultdict(deque)
        self.command_logs = deque(maxlen=10000)
        self.event_logs = deque(maxlen=10000) 
        self.error_logs = deque(maxlen=5000)
        
        # Analytics cache
        self.analytics_cache = {}
        self.cache_ttl = 60  # seconds
        
        # Performance tracking
        self.performance_baselines = {}
        self.anomaly_thresholds = {}
        
        # Predictive models (simple moving averages for now)
        self.prediction_models = {}
        
        # Initialize default thresholds
        self._initialize_thresholds()
        
        # Start background analytics tasks
        self.analytics_tasks = []
        self._start_background_tasks()
    
    def _initialize_thresholds(self):
        """Initialize default anomaly detection thresholds"""
        self.anomaly_thresholds = {
            "cpu_usage": {"warning": 80, "critical": 95},
            "memory_usage": {"warning": 85, "critical": 95},
            "temperature": {"warning": 70, "critical": 85},
            "error_rate": {"warning": 5, "critical": 15},
            "latency": {"warning": 100, "critical": 500},
            "bandwidth_usage": {"warning": 80, "critical": 95},
            "disk_usage": {"warning": 85, "critical": 95}
        }
    
    def _start_background_tasks(self):
        """Start background analytics processing tasks"""
        self.analytics_tasks = [
            asyncio.create_task(self._periodic_analytics()),
            asyncio.create_task(self._anomaly_detection()),
            asyncio.create_task(self._cache_cleanup()),
            asyncio.create_task(self._trend_analysis())
        ]
    
    async def record_metric(self, device_id: str, metric_name: str, value: float, metadata: Dict[str, Any] = None):
        """Record a metric data point"""
        try:
            metric_point = MetricPoint(
                timestamp=datetime.now(),
                value=value,
                metadata=metadata or {}
            )
            
            # Store in device metrics
            device_metrics = self.metrics_storage[device_id][metric_name]
            device_metrics.append(metric_point)
            
            # Keep only last 1000 points per metric
            if len(device_metrics) > 1000:
                device_metrics.popleft()
            
            # Update system-wide metrics
            system_metric_name = f"system_{metric_name}"
            self.system_metrics[system_metric_name].append(metric_point)
            if len(self.system_metrics[system_metric_name]) > 5000:
                self.system_metrics[system_metric_name].popleft()
            
            # Clear cache for affected device
            cache_key = f"device_metrics_{device_id}"
            if cache_key in self.analytics_cache:
                del self.analytics_cache[cache_key]
            
        except Exception as e:
            logger.error(f"Error recording metric {metric_name} for device {device_id}: {e}")
    
    async def log_command_execution(self, device_id: str, command: str, execution_time: float, 
                                  status: str, result: Any = None):
        """Log command execution for analytics"""
        try:
            log_entry = {
                "timestamp": datetime.now(),
                "device_id": device_id,
                "command": command,
                "execution_time": execution_time,
                "status": status,
                "result_size": len(str(result)) if result else 0,
                "success": status == "success"
            }
            
            self.command_logs.append(log_entry)
            
            # Record metrics
            await self.record_metric(device_id, "command_execution_time", execution_time)
            await self.record_metric(device_id, "command_success_rate", 1.0 if status == "success" else 0.0)
            
        except Exception as e:
            logger.error(f"Error logging command execution: {e}")
    
    async def log_event(self, device_id: str, event_type: str, severity: str, details: Dict[str, Any]):
        """Log device event for analytics"""
        try:
            event_entry = {
                "timestamp": datetime.now(),
                "device_id": device_id,
                "event_type": event_type,
                "severity": severity,
                "details": details
            }
            
            self.event_logs.append(event_entry)
            
            # Log errors separately
            if severity in ["error", "critical"]:
                self.error_logs.append(event_entry)
                await self.record_metric(device_id, "error_count", 1.0)
            
        except Exception as e:
            logger.error(f"Error logging event: {e}")
    
    async def get_device_metrics(self, device_id: str, time_range: str = "1h") -> Dict[str, Any]:
        """Get comprehensive device metrics"""
        try:
            cache_key = f"device_metrics_{device_id}_{time_range}"
            
            # Check cache
            if cache_key in self.analytics_cache:
                cache_entry = self.analytics_cache[cache_key]
                if datetime.now() - cache_entry["timestamp"] < timedelta(seconds=self.cache_ttl):
                    return cache_entry["data"]
            
            # Calculate time window
            time_window = self._parse_time_range(time_range)
            cutoff_time = datetime.now() - time_window
            
            device_metrics = self.metrics_storage.get(device_id, {})
            result = {}
            
            for metric_name, metric_points in device_metrics.items():
                # Filter by time range
                recent_points = [p for p in metric_points if p.timestamp >= cutoff_time]
                
                if recent_points:
                    values = [p.value for p in recent_points]
                    result[metric_name] = {
                        "current": values[-1],
                        "average": statistics.mean(values),
                        "min": min(values),
                        "max": max(values),
                        "median": statistics.median(values),
                        "stddev": statistics.stdev(values) if len(values) > 1 else 0,
                        "count": len(values),
                        "trend": await self._calculate_trend(values)
                    }
                else:
                    result[metric_name] = {
                        "current": None,
                        "average": None,
                        "min": None,
                        "max": None,
                        "median": None,
                        "stddev": None,
                        "count": 0,
                        "trend": "no_data"
                    }
            
            # Cache result
            self.analytics_cache[cache_key] = {
                "timestamp": datetime.now(),
                "data": result
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting device metrics for {device_id}: {e}")
            return {}
    
    async def get_real_time_metrics(self, device_id: str) -> Dict[str, Any]:
        """Get current real-time metrics for device"""
        try:
            device_metrics = self.metrics_storage.get(device_id, {})
            result = {}
            
            for metric_name, metric_points in device_metrics.items():
                if metric_points:
                    latest_point = metric_points[-1]
                    result[metric_name] = {
                        "value": latest_point.value,
                        "timestamp": latest_point.timestamp.isoformat(),
                        "metadata": latest_point.metadata
                    }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting real-time metrics for {device_id}: {e}")
            return {}
    
    async def get_detailed_metrics(self, device_id: str) -> Dict[str, Any]:
        """Get detailed metrics with historical data"""
        try:
            # Get basic metrics
            metrics = await self.get_device_metrics(device_id, "24h")
            
            # Add performance analysis
            performance_score = await self._calculate_performance_score(device_id)
            health_score = await self._calculate_health_score(device_id)
            efficiency_rating = await self._calculate_efficiency_rating(device_id)
            
            # Add trend analysis
            trends = await self._analyze_device_trends(device_id)
            
            # Add anomalies
            anomalies = await self._detect_device_anomalies(device_id)
            
            return {
                "metrics": metrics,
                "performance_score": performance_score,
                "health_score": health_score,
                "efficiency_rating": efficiency_rating,
                "trends": trends,
                "anomalies": anomalies,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting detailed metrics for {device_id}: {e}")
            return {}
    
    async def get_performance_trends(self, device_id: str, days: int = 7) -> Dict[str, List[float]]:
        """Get performance trends over time"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            device_metrics = self.metrics_storage.get(device_id, {})
            trends = {}
            
            for metric_name, metric_points in device_metrics.items():
                # Filter by time range
                recent_points = [p for p in metric_points if p.timestamp >= cutoff_time]
                
                if recent_points:
                    # Group by hour and calculate averages
                    hourly_data = defaultdict(list)
                    for point in recent_points:
                        hour_key = point.timestamp.strftime("%Y-%m-%d %H:00")
                        hourly_data[hour_key].append(point.value)
                    
                    # Calculate hourly averages
                    hourly_averages = []
                    for hour in sorted(hourly_data.keys()):
                        avg = statistics.mean(hourly_data[hour])
                        hourly_averages.append(avg)
                    
                    trends[metric_name] = hourly_averages
            
            return trends
            
        except Exception as e:
            logger.error(f"Error getting performance trends for {device_id}: {e}")
            return {}
    
    async def get_device_history(self, device_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get device event history"""
        try:
            # Filter events for this device
            device_events = [
                {
                    "timestamp": event["timestamp"].isoformat(),
                    "event_type": event["event_type"],
                    "severity": event["severity"],
                    "details": event["details"]
                }
                for event in self.event_logs
                if event["device_id"] == device_id
            ]
            
            # Sort by timestamp (newest first) and limit
            device_events.sort(key=lambda x: x["timestamp"], reverse=True)
            return device_events[:limit]
            
        except Exception as e:
            logger.error(f"Error getting device history for {device_id}: {e}")
            return []
    
    async def get_system_analytics(self, time_range: str = "24h") -> Dict[str, Any]:
        """Get comprehensive system analytics"""
        try:
            time_window = self._parse_time_range(time_range)
            cutoff_time = datetime.now() - time_window
            
            # Device statistics
            total_devices = len(self.metrics_storage)
            active_devices = 0
            device_types = defaultdict(int)
            
            # Command statistics
            recent_commands = [cmd for cmd in self.command_logs if cmd["timestamp"] >= cutoff_time]
            total_commands = len(recent_commands)
            successful_commands = sum(1 for cmd in recent_commands if cmd["success"])
            
            # Error statistics
            recent_errors = [err for err in self.error_logs if err["timestamp"] >= cutoff_time]
            total_errors = len(recent_errors)
            
            # Performance metrics
            system_health_scores = []
            for device_id in self.metrics_storage.keys():
                health_score = await self._calculate_health_score(device_id)
                if health_score > 0:
                    system_health_scores.append(health_score)
                    active_devices += 1
            
            avg_health_score = statistics.mean(system_health_scores) if system_health_scores else 0
            
            # Data transfer statistics
            total_data_gb = 0
            for device_id, metrics in self.metrics_storage.items():
                if "data_transferred" in metrics:
                    recent_data = [p.value for p in metrics["data_transferred"] if p.timestamp >= cutoff_time]
                    total_data_gb += sum(recent_data)
            
            return {
                "time_range": time_range,
                "total_devices": total_devices,
                "active_devices": active_devices,
                "device_types_breakdown": dict(device_types),
                "protocol_usage": await self._get_protocol_usage_stats(),
                "average_health_score": avg_health_score,
                "total_data_transferred": total_data_gb,
                "commands_executed": total_commands,
                "success_rate": (successful_commands / total_commands * 100) if total_commands > 0 else 100,
                "error_rate": (total_errors / max(total_commands, 1) * 100),
                "performance_trends": await self._get_system_performance_trends(),
                "top_performing_devices": await self._get_top_performing_devices(),
                "devices_needing_attention": await self._get_devices_needing_attention(),
                "system_load": await self._calculate_system_load(),
                "uptime_stats": await self._get_uptime_stats()
            }
            
        except Exception as e:
            logger.error(f"Error getting system analytics: {e}")
            return {}
    
    async def generate_device_insights(self, device_id: str) -> Dict[str, Any]:
        """Generate AI-powered insights for device"""
        try:
            # Get comprehensive device data
            metrics = await self.get_detailed_metrics(device_id)
            command_history = [cmd for cmd in self.command_logs if cmd["device_id"] == device_id]
            error_history = [err for err in self.error_logs if err["device_id"] == device_id]
            
            # Calculate insights
            insights = {
                "device_id": device_id,
                "overall_score": metrics.get("performance_score", 0.5),
                "efficiency_rating": metrics.get("efficiency_rating", "C"),
                "usage_pattern": await self._analyze_usage_pattern(device_id),
                "performance_predictions": await self._generate_performance_predictions(device_id),
                "optimization_recommendations": await self._generate_optimization_recommendations(device_id),
                "anomalies_detected": metrics.get("anomalies", []),
                "comparative_analysis": await self._compare_with_similar_devices(device_id),
                "cost_analysis": await self._calculate_cost_analysis(device_id),
                "maintenance_recommendations": await self._generate_maintenance_recommendations(device_id),
                "risk_assessment": await self._assess_device_risks(device_id)
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating insights for device {device_id}: {e}")
            return {}
    
    async def get_performance_config(self) -> Dict[str, Any]:
        """Get performance analytics configuration"""
        return {
            "cache_ttl_seconds": self.cache_ttl,
            "max_metrics_per_device": 1000,
            "max_system_metrics": 5000,
            "anomaly_thresholds": self.anomaly_thresholds,
            "analytics_enabled": True,
            "predictive_analytics_enabled": True,
            "real_time_processing": True
        }
    
    # Private helper methods
    
    def _parse_time_range(self, time_range: str) -> timedelta:
        """Parse time range string to timedelta"""
        try:
            if time_range.endswith('h'):
                hours = int(time_range[:-1])
                return timedelta(hours=hours)
            elif time_range.endswith('d'):
                days = int(time_range[:-1])
                return timedelta(days=days)
            elif time_range.endswith('m'):
                minutes = int(time_range[:-1])
                return timedelta(minutes=minutes)
            else:
                return timedelta(hours=1)  # default
        except:
            return timedelta(hours=1)
    
    async def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from values"""
        if len(values) < 2:
            return "insufficient_data"
        
        # Simple linear regression slope
        n = len(values)
        x = list(range(n))
        
        # Calculate slope
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return "stable"
        
        slope = numerator / denominator
        
        if slope > 0.01:
            return "increasing"
        elif slope < -0.01:
            return "decreasing"
        else:
            return "stable"
    
    async def _calculate_performance_score(self, device_id: str) -> float:
        """Calculate overall performance score for device"""
        try:
            recent_metrics = await self.get_device_metrics(device_id, "1h")
            
            if not recent_metrics:
                return 0.5  # neutral score for no data
            
            score = 1.0
            
            # Factor in various metrics
            if "error_rate" in recent_metrics and recent_metrics["error_rate"]["current"] is not None:
                error_rate = recent_metrics["error_rate"]["current"]
                score *= max(0, 1.0 - error_rate / 100.0)
            
            if "latency" in recent_metrics and recent_metrics["latency"]["current"] is not None:
                latency = recent_metrics["latency"]["current"]
                # Penalize high latency (normalize to 0-1 range)
                score *= max(0, 1.0 - min(latency / 1000.0, 1.0))
            
            if "cpu_usage" in recent_metrics and recent_metrics["cpu_usage"]["current"] is not None:
                cpu_usage = recent_metrics["cpu_usage"]["current"]
                # Optimal CPU usage is around 60-80%
                if cpu_usage < 60:
                    score *= 0.8  # underutilized
                elif cpu_usage > 90:
                    score *= 0.6  # overloaded
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"Error calculating performance score for {device_id}: {e}")
            return 0.5
    
    async def _calculate_health_score(self, device_id: str) -> float:
        """Calculate health score for device"""
        try:
            recent_metrics = await self.get_device_metrics(device_id, "24h")
            recent_errors = [err for err in self.error_logs 
                           if err["device_id"] == device_id and 
                           err["timestamp"] >= datetime.now() - timedelta(hours=24)]
            
            health_score = 1.0
            
            # Factor in error rate
            if recent_errors:
                error_penalty = min(len(recent_errors) / 10.0, 0.5)  # Max 50% penalty
                health_score -= error_penalty
            
            # Factor in temperature if available
            if "temperature" in recent_metrics:
                temp = recent_metrics["temperature"].get("current")
                if temp and temp > 80:  # High temperature
                    health_score *= 0.7
                elif temp and temp > 70:
                    health_score *= 0.9
            
            # Factor in uptime/availability
            command_history = [cmd for cmd in self.command_logs if cmd["device_id"] == device_id]
            if command_history:
                recent_commands = [cmd for cmd in command_history 
                                 if cmd["timestamp"] >= datetime.now() - timedelta(hours=24)]
                success_rate = sum(1 for cmd in recent_commands if cmd["success"]) / len(recent_commands)
                health_score *= success_rate
            
            return max(0.0, min(1.0, health_score))
            
        except Exception as e:
            logger.error(f"Error calculating health score for {device_id}: {e}")
            return 0.5
    
    async def _calculate_efficiency_rating(self, device_id: str) -> str:
        """Calculate efficiency rating (A+ to F)"""
        try:
            performance_score = await self._calculate_performance_score(device_id)
            health_score = await self._calculate_health_score(device_id)
            
            overall_score = (performance_score + health_score) / 2.0
            
            if overall_score >= 0.95:
                return "A+"
            elif overall_score >= 0.90:
                return "A"
            elif overall_score >= 0.85:
                return "A-"
            elif overall_score >= 0.80:
                return "B+"
            elif overall_score >= 0.75:
                return "B"
            elif overall_score >= 0.70:
                return "B-"
            elif overall_score >= 0.65:
                return "C+"
            elif overall_score >= 0.60:
                return "C"
            elif overall_score >= 0.50:
                return "C-"
            elif overall_score >= 0.40:
                return "D"
            else:
                return "F"
                
        except Exception as e:
            logger.error(f"Error calculating efficiency rating for {device_id}: {e}")
            return "C"
    
    async def _analyze_device_trends(self, device_id: str) -> List[PerformanceTrend]:
        """Analyze performance trends for device"""
        trends = []
        
        try:
            device_metrics = self.metrics_storage.get(device_id, {})
            
            for metric_name, metric_points in device_metrics.items():
                if len(metric_points) >= 10:  # Need at least 10 points for trend analysis
                    values = [p.value for p in metric_points[-20:]]  # Last 20 points
                    
                    trend_direction = await self._calculate_trend(values)
                    trend_strength = await self._calculate_trend_strength(values)
                    prediction = await self._predict_next_value(values)
                    
                    trend = PerformanceTrend(
                        metric_name=metric_name,
                        current_value=values[-1],
                        trend_direction=trend_direction,
                        trend_strength=trend_strength,
                        prediction=prediction,
                        confidence=0.7 if len(values) >= 20 else 0.5
                    )
                    trends.append(trend)
            
        except Exception as e:
            logger.error(f"Error analyzing trends for device {device_id}: {e}")
        
        return trends
    
    async def _calculate_trend_strength(self, values: List[float]) -> float:
        """Calculate strength of trend (0-1)"""
        try:
            if len(values) < 3:
                return 0.0
            
            # Calculate correlation coefficient with linear sequence
            n = len(values)
            x = list(range(n))
            
            # Pearson correlation coefficient
            x_mean = sum(x) / n
            y_mean = sum(values) / n
            
            numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
            x_var = sum((x[i] - x_mean) ** 2 for i in range(n))
            y_var = sum((values[i] - y_mean) ** 2 for i in range(n))
            
            if x_var == 0 or y_var == 0:
                return 0.0
            
            correlation = numerator / (x_var * y_var) ** 0.5
            return abs(correlation)
            
        except:
            return 0.0
    
    async def _predict_next_value(self, values: List[float]) -> float:
        """Simple prediction of next value using linear trend"""
        try:
            if len(values) < 2:
                return values[0] if values else 0.0
            
            # Simple linear extrapolation
            recent_trend = values[-1] - values[-2]
            prediction = values[-1] + recent_trend
            
            return prediction
            
        except:
            return values[-1] if values else 0.0
    
    async def _detect_device_anomalies(self, device_id: str) -> List[Dict[str, Any]]:
        """Detect anomalies in device behavior"""
        anomalies = []
        
        try:
            recent_metrics = await self.get_device_metrics(device_id, "1h")
            
            for metric_name, metric_data in recent_metrics.items():
                if metric_name in self.anomaly_thresholds and metric_data["current"] is not None:
                    thresholds = self.anomaly_thresholds[metric_name]
                    current_value = metric_data["current"]
                    
                    severity = None
                    if current_value >= thresholds["critical"]:
                        severity = "critical"
                    elif current_value >= thresholds["warning"]:
                        severity = "warning"
                    
                    if severity:
                        anomalies.append({
                            "metric_name": metric_name,
                            "current_value": current_value,
                            "threshold": thresholds[severity],
                            "severity": severity,
                            "detected_at": datetime.now().isoformat()
                        })
        
        except Exception as e:
            logger.error(f"Error detecting anomalies for device {device_id}: {e}")
        
        return anomalies
    
    # Background processing tasks
    
    async def _periodic_analytics(self):
        """Periodic analytics processing"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                # Update performance baselines
                await self._update_performance_baselines()
                
                # Generate predictions
                await self._update_predictions()
                
            except Exception as e:
                logger.error(f"Error in periodic analytics: {e}")
    
    async def _anomaly_detection(self):
        """Background anomaly detection"""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                # Check all active devices for anomalies
                for device_id in self.metrics_storage.keys():
                    anomalies = await self._detect_device_anomalies(device_id)
                    
                    # Log significant anomalies
                    for anomaly in anomalies:
                        if anomaly["severity"] == "critical":
                            await self.log_event(
                                device_id, 
                                "anomaly_detected", 
                                "critical",
                                anomaly
                            )
                
            except Exception as e:
                logger.error(f"Error in anomaly detection: {e}")
    
    async def _cache_cleanup(self):
        """Clean up expired cache entries"""
        while True:
            try:
                await asyncio.sleep(600)  # Run every 10 minutes
                
                current_time = datetime.now()
                expired_keys = []
                
                for key, entry in self.analytics_cache.items():
                    if current_time - entry["timestamp"] > timedelta(seconds=self.cache_ttl * 2):
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self.analytics_cache[key]
                
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
                
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
    
    async def _trend_analysis(self):
        """Background trend analysis"""
        while True:
            try:
                await asyncio.sleep(1800)  # Run every 30 minutes
                
                # Update trend analysis for all devices
                for device_id in self.metrics_storage.keys():
                    trends = await self._analyze_device_trends(device_id)
                    
                    # Store trends for later use
                    cache_key = f"trends_{device_id}"
                    self.analytics_cache[cache_key] = {
                        "timestamp": datetime.now(),
                        "data": [asdict(trend) for trend in trends]
                    }
                
            except Exception as e:
                logger.error(f"Error in trend analysis: {e}")
    
    # Additional helper methods (placeholder implementations)
    
    async def _get_protocol_usage_stats(self) -> Dict[str, int]:
        """Get protocol usage statistics"""
        # Placeholder implementation
        return {"usb": 45, "ethernet": 30, "wifi": 20, "bluetooth": 5}
    
    async def _get_system_performance_trends(self) -> Dict[str, List[float]]:
        """Get system-wide performance trends"""
        # Placeholder implementation
        return {"cpu": [60, 65, 70, 68, 72], "memory": [75, 80, 78, 82, 79]}
    
    async def _get_top_performing_devices(self) -> List[str]:
        """Get list of top performing device IDs"""
        device_scores = []
        for device_id in self.metrics_storage.keys():
            score = await self._calculate_performance_score(device_id)
            device_scores.append((device_id, score))
        
        device_scores.sort(key=lambda x: x[1], reverse=True)
        return [device_id for device_id, score in device_scores[:5]]
    
    async def _get_devices_needing_attention(self) -> List[str]:
        """Get list of devices needing attention"""
        attention_devices = []
        for device_id in self.metrics_storage.keys():
            health_score = await self._calculate_health_score(device_id)
            if health_score < 0.7:
                attention_devices.append(device_id)
        
        return attention_devices[:10]  # Limit to top 10
    
    async def _calculate_system_load(self) -> Dict[str, float]:
        """Calculate current system load"""
        return {"cpu": 65.0, "memory": 78.0, "network": 45.0, "storage": 60.0}
    
    async def _get_uptime_stats(self) -> Dict[str, Any]:
        """Get system uptime statistics"""
        return {"system_uptime_hours": 168.5, "average_device_uptime": 95.2}
    
    # Advanced analytics methods (placeholder implementations)
    
    async def _analyze_usage_pattern(self, device_id: str) -> Dict[str, Any]:
        """Analyze device usage patterns"""
        return {
            "peak_usage_hours": [9, 10, 14, 15, 16],
            "usage_frequency": "high",
            "seasonal_patterns": "weekday_heavy"
        }
    
    async def _generate_performance_predictions(self, device_id: str) -> Dict[str, Any]:
        """Generate performance predictions"""
        return {
            "next_24h": {"health_score": 0.85, "performance_score": 0.80},
            "next_week": {"health_score": 0.82, "performance_score": 0.78},
            "confidence": 0.75
        }
    
    async def _generate_optimization_recommendations(self, device_id: str) -> List[str]:
        """Generate optimization recommendations"""
        return [
            "Consider upgrading firmware to latest version",
            "Reduce polling frequency during low-usage hours",
            "Enable power management features"
        ]
    
    async def _compare_with_similar_devices(self, device_id: str) -> Dict[str, Any]:
        """Compare device with similar devices"""
        return {
            "percentile_rank": 75,
            "better_than_percent": 75,
            "similar_device_count": 12,
            "comparison_metrics": {
                "performance": "above_average",
                "reliability": "excellent",
                "efficiency": "good"
            }
        }
    
    async def _calculate_cost_analysis(self, device_id: str) -> Dict[str, Any]:
        """Calculate cost analysis for device"""
        return {
            "estimated_monthly_cost": 25.50,
            "cost_per_operation": 0.002,
            "efficiency_rating": "B+",
            "cost_trend": "stable"
        }
    
    async def _generate_maintenance_recommendations(self, device_id: str) -> List[str]:
        """Generate maintenance recommendations"""
        return [
            "Schedule routine maintenance check in 2 weeks",
            "Monitor temperature trends closely",
            "Update device drivers"
        ]
    
    async def _assess_device_risks(self, device_id: str) -> Dict[str, Any]:
        """Assess device risks"""
        return {
            "overall_risk": "low",
            "failure_probability": 0.15,
            "risk_factors": ["age", "usage_intensity"],
            "mitigation_actions": ["preventive_maintenance", "monitoring_increase"]
        }
    
    async def _update_performance_baselines(self):
        """Update performance baselines for all devices"""
        pass
    
    async def _update_predictions(self):
        """Update ML predictions for all devices"""
        pass