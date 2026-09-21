import time
import sqlite3
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import json
import threading
import queue


@dataclass
class MetricValue:
    timestamp: datetime
    model_id: str
    model_version: str
    metric_name: str
    metric_value: float
    metadata: Dict[str, Any]


@dataclass
class PerformanceAlert:
    alert_id: str
    model_id: str
    model_version: str
    metric_name: str
    threshold: float
    current_value: float
    severity: str  # 'low', 'medium', 'high', 'critical'
    timestamp: datetime
    message: str


class MetricCollector:
    def __init__(self):
        self.metrics_queue = queue.Queue()
        self.is_collecting = False
        self.collection_thread = None
    
    def start_collection(self):
        self.is_collecting = True
        self.collection_thread = threading.Thread(target=self._collect_metrics)
        self.collection_thread.daemon = True
        self.collection_thread.start()
    
    def stop_collection(self):
        self.is_collecting = False
        if self.collection_thread:
            self.collection_thread.join()
    
    def record_inference(self, model_id: str, model_version: str, 
                        latency: float, prediction: Any, 
                        actual: Optional[Any] = None, 
                        metadata: Optional[Dict[str, Any]] = None):
        timestamp = datetime.now()
        metadata = metadata or {}
        
        # Record latency
        self.metrics_queue.put(MetricValue(
            timestamp=timestamp,
            model_id=model_id,
            model_version=model_version,
            metric_name="inference_latency",
            metric_value=latency,
            metadata={**metadata, "prediction": str(prediction)}
        ))
        
        # Record accuracy if actual value provided
        if actual is not None:
            accuracy = 1.0 if prediction == actual else 0.0
            self.metrics_queue.put(MetricValue(
                timestamp=timestamp,
                model_id=model_id,
                model_version=model_version,
                metric_name="accuracy",
                metric_value=accuracy,
                metadata={**metadata, "prediction": str(prediction), "actual": str(actual)}
            ))
    
    def record_custom_metric(self, model_id: str, model_version: str,
                           metric_name: str, value: float,
                           metadata: Optional[Dict[str, Any]] = None):
        self.metrics_queue.put(MetricValue(
            timestamp=datetime.now(),
            model_id=model_id,
            model_version=model_version,
            metric_name=metric_name,
            metric_value=value,
            metadata=metadata or {}
        ))
    
    def _collect_metrics(self):
        while self.is_collecting:
            try:
                metric = self.metrics_queue.get(timeout=1)
                # In real implementation, would send to monitoring system
                print(f"Collected metric: {metric.metric_name}={metric.metric_value} for {metric.model_id}:{metric.model_version}")
            except queue.Empty:
                continue


class PerformanceMonitor:
    def __init__(self, db_path: str = "ml_platform.db"):
        self.db_path = db_path
        self.metric_collector = MetricCollector()
        self.alert_thresholds = {}
        self.alert_callbacks = []
        self._init_database()
    
    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                model_id TEXT NOT NULL,
                model_version TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metadata TEXT,
                INDEX (model_id, model_version, metric_name, timestamp)
            )
        ''')
        
        # Create alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_alerts (
                alert_id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                model_version TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                threshold REAL NOT NULL,
                current_value REAL NOT NULL,
                severity TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                message TEXT NOT NULL,
                resolved BOOLEAN DEFAULT FALSE
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def start_monitoring(self):
        self.metric_collector.start_collection()
    
    def stop_monitoring(self):
        self.metric_collector.stop_collection()
    
    def record_metric(self, model_id: str, model_version: str,
                     metric_name: str, value: float,
                     metadata: Optional[Dict[str, Any]] = None):
        metric = MetricValue(
            timestamp=datetime.now(),
            model_id=model_id,
            model_version=model_version,
            metric_name=metric_name,
            metric_value=value,
            metadata=metadata or {}
        )
        
        # Store in database
        self._store_metric(metric)
        
        # Check alerts
        self._check_alerts(metric)
    
    def record_inference_metrics(self, model_id: str, model_version: str,
                               latency: float, prediction: Any,
                               actual: Optional[Any] = None,
                               metadata: Optional[Dict[str, Any]] = None):
        # Record via collector for real-time processing
        self.metric_collector.record_inference(
            model_id, model_version, latency, prediction, actual, metadata
        )
        
        # Also store directly for immediate analysis
        self.record_metric(model_id, model_version, "inference_latency", latency, metadata)
        
        if actual is not None:
            accuracy = 1.0 if prediction == actual else 0.0
            self.record_metric(model_id, model_version, "accuracy", accuracy, metadata)
    
    def _store_metric(self, metric: MetricValue):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO performance_metrics 
            (timestamp, model_id, model_version, metric_name, metric_value, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            metric.timestamp.isoformat(),
            metric.model_id,
            metric.model_version,
            metric.metric_name,
            metric.metric_value,
            json.dumps(metric.metadata)
        ))
        
        conn.commit()
        conn.close()
    
    def set_alert_threshold(self, model_id: str, model_version: str,
                          metric_name: str, threshold: float,
                          comparison: str = "greater_than",
                          severity: str = "medium"):
        key = f"{model_id}:{model_version}:{metric_name}"
        self.alert_thresholds[key] = {
            "threshold": threshold,
            "comparison": comparison,
            "severity": severity
        }
    
    def _check_alerts(self, metric: MetricValue):
        key = f"{metric.model_id}:{metric.model_version}:{metric.metric_name}"
        if key not in self.alert_thresholds:
            return
        
        threshold_config = self.alert_thresholds[key]
        threshold = threshold_config["threshold"]
        comparison = threshold_config["comparison"]
        severity = threshold_config["severity"]
        
        should_alert = False
        if comparison == "greater_than" and metric.metric_value > threshold:
            should_alert = True
        elif comparison == "less_than" and metric.metric_value < threshold:
            should_alert = True
        elif comparison == "equal" and abs(metric.metric_value - threshold) < 0.001:
            should_alert = True
        
        if should_alert:
            alert = PerformanceAlert(
                alert_id=f"alert_{int(time.time())}_{metric.model_id}",
                model_id=metric.model_id,
                model_version=metric.model_version,
                metric_name=metric.metric_name,
                threshold=threshold,
                current_value=metric.metric_value,
                severity=severity,
                timestamp=metric.timestamp,
                message=f"{metric.metric_name} {comparison} {threshold}: {metric.metric_value}"
            )
            
            self._store_alert(alert)
            self._trigger_alert_callbacks(alert)
    
    def _store_alert(self, alert: PerformanceAlert):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO performance_alerts 
            (alert_id, model_id, model_version, metric_name, threshold, 
             current_value, severity, timestamp, message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            alert.alert_id,
            alert.model_id,
            alert.model_version,
            alert.metric_name,
            alert.threshold,
            alert.current_value,
            alert.severity,
            alert.timestamp.isoformat(),
            alert.message
        ))
        
        conn.commit()
        conn.close()
    
    def _trigger_alert_callbacks(self, alert: PerformanceAlert):
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"Error in alert callback: {e}")
    
    def add_alert_callback(self, callback):
        self.alert_callbacks.append(callback)
    
    def get_metrics(self, model_id: str, model_version: str,
                   metric_name: Optional[str] = None,
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None) -> List[MetricValue]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT timestamp, model_id, model_version, metric_name, metric_value, metadata
            FROM performance_metrics 
            WHERE model_id = ? AND model_version = ?
        '''
        params = [model_id, model_version]
        
        if metric_name:
            query += " AND metric_name = ?"
            params.append(metric_name)
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        query += " ORDER BY timestamp DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        metrics = []
        for row in rows:
            metrics.append(MetricValue(
                timestamp=datetime.fromisoformat(row[0]),
                model_id=row[1],
                model_version=row[2],
                metric_name=row[3],
                metric_value=row[4],
                metadata=json.loads(row[5]) if row[5] else {}
            ))
        
        return metrics
    
    def get_model_summary(self, model_id: str, model_version: str,
                         hours: int = 24) -> Dict[str, Any]:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        metrics = self.get_metrics(model_id, model_version, 
                                 start_time=start_time, end_time=end_time)
        
        # Group metrics by type
        grouped_metrics = defaultdict(list)
        for metric in metrics:
            grouped_metrics[metric.metric_name].append(metric.metric_value)
        
        summary = {
            "model_id": model_id,
            "model_version": model_version,
            "time_period": f"Last {hours} hours",
            "total_predictions": len([m for m in metrics if m.metric_name == "inference_latency"]),
            "metrics": {}
        }
        
        for metric_name, values in grouped_metrics.items():
            if values:
                summary["metrics"][metric_name] = {
                    "count": len(values),
                    "average": statistics.mean(values),
                    "min": min(values),
                    "max": max(values),
                    "median": statistics.median(values)
                }
                
                if len(values) > 1:
                    summary["metrics"][metric_name]["std_dev"] = statistics.stdev(values)
        
        return summary
    
    def get_active_alerts(self, model_id: Optional[str] = None,
                         severity: Optional[str] = None) -> List[PerformanceAlert]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM performance_alerts WHERE resolved = FALSE"
        params = []
        
        if model_id:
            query += " AND model_id = ?"
            params.append(model_id)
        
        if severity:
            query += " AND severity = ?"
            params.append(severity)
        
        query += " ORDER BY timestamp DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        alerts = []
        for row in rows:
            alerts.append(PerformanceAlert(
                alert_id=row[0],
                model_id=row[1],
                model_version=row[2],
                metric_name=row[3],
                threshold=row[4],
                current_value=row[5],
                severity=row[6],
                timestamp=datetime.fromisoformat(row[7]),
                message=row[8]
            ))
        
        return alerts
    
    def resolve_alert(self, alert_id: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE performance_alerts 
            SET resolved = TRUE 
            WHERE alert_id = ?
        ''', (alert_id,))
        
        conn.commit()
        conn.close()
    
    def get_performance_trends(self, model_id: str, model_version: str,
                             metric_name: str, days: int = 7) -> Dict[str, Any]:
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        metrics = self.get_metrics(model_id, model_version, metric_name,
                                 start_time=start_time, end_time=end_time)
        
        if not metrics:
            return {"trend": "no_data", "metrics": []}
        
        # Group by day
        daily_averages = defaultdict(list)
        for metric in metrics:
            day_key = metric.timestamp.date()
            daily_averages[day_key].append(metric.metric_value)
        
        # Calculate daily averages
        trend_data = []
        for day in sorted(daily_averages.keys()):
            values = daily_averages[day]
            trend_data.append({
                "date": day.isoformat(),
                "average": statistics.mean(values),
                "count": len(values),
                "min": min(values),
                "max": max(values)
            })
        
        # Calculate trend direction
        if len(trend_data) >= 2:
            first_avg = trend_data[0]["average"]
            last_avg = trend_data[-1]["average"]
            
            if last_avg > first_avg * 1.05:
                trend = "increasing"
            elif last_avg < first_avg * 0.95:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "model_id": model_id,
            "model_version": model_version,
            "metric_name": metric_name,
            "trend": trend,
            "days": days,
            "daily_data": trend_data
        }


class ModelHealthCheck:
    def __init__(self, performance_monitor: PerformanceMonitor):
        self.monitor = performance_monitor
    
    def check_model_health(self, model_id: str, model_version: str) -> Dict[str, Any]:
        summary = self.monitor.get_model_summary(model_id, model_version)
        alerts = self.monitor.get_active_alerts(model_id)
        
        # Determine health score
        health_score = 100
        health_status = "healthy"
        issues = []
        
        # Check for alerts
        critical_alerts = [a for a in alerts if a.severity == "critical"]
        high_alerts = [a for a in alerts if a.severity == "high"]
        
        if critical_alerts:
            health_score -= 40
            health_status = "critical"
            issues.extend([f"Critical alert: {alert.message}" for alert in critical_alerts])
        elif high_alerts:
            health_score -= 25
            health_status = "degraded"
            issues.extend([f"High severity alert: {alert.message}" for alert in high_alerts])
        
        # Check metrics
        if "metrics" in summary:
            # Check latency
            if "inference_latency" in summary["metrics"]:
                latency = summary["metrics"]["inference_latency"]
                if latency["average"] > 1000:  # 1 second
                    health_score -= 20
                    issues.append(f"High average latency: {latency['average']:.2f}ms")
            
            # Check accuracy
            if "accuracy" in summary["metrics"]:
                accuracy = summary["metrics"]["accuracy"]
                if accuracy["average"] < 0.8:
                    health_score -= 30
                    issues.append(f"Low accuracy: {accuracy['average']:.2%}")
        
        if health_score < 70 and health_status == "healthy":
            health_status = "degraded"
        elif health_score < 40 and health_status != "critical":
            health_status = "unhealthy"
        
        return {
            "model_id": model_id,
            "model_version": model_version,
            "health_score": max(0, health_score),
            "health_status": health_status,
            "issues": issues,
            "summary": summary,
            "active_alerts": len(alerts)
        }


# Usage example
if __name__ == "__main__":
    monitor = PerformanceMonitor()
    monitor.start_monitoring()
    
    # Set up alerts
    monitor.set_alert_threshold("model_v1", "1.0", "inference_latency", 500, "greater_than", "high")
    monitor.set_alert_threshold("model_v1", "1.0", "accuracy", 0.8, "less_than", "critical")
    
    # Add alert callback
    def alert_handler(alert: PerformanceAlert):
        print(f"ALERT [{alert.severity}]: {alert.message}")
    
    monitor.add_alert_callback(alert_handler)
    
    # Record some metrics
    monitor.record_inference_metrics("model_v1", "1.0", 250.5, "positive", "positive")
    monitor.record_inference_metrics("model_v1", "1.0", 180.2, "negative", "positive")  # Wrong prediction
    
    # Check model health
    health_checker = ModelHealthCheck(monitor)
    health = health_checker.check_model_health("model_v1", "1.0")
    print(f"Model health: {health['health_status']} (score: {health['health_score']})")
    
    monitor.stop_monitoring()